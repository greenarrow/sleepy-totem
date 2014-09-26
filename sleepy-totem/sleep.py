from gi.repository import GObject, Peas, Totem, Gtk # pylint: disable-msg=E0611
import os, threading, time, dbus, math
from __builtin__ import getattr


# Seconds between checks of Totem state
POLLING_PERIOD = 5
# Seconds warning dialog is displayed before action
WARNING_TIMEOUT = 120

# Enable testing mode (does not call real action)
#TESTING = True
TESTING = False

# State constants
SLEEP_MODE_DISABLED = "disabled"
SLEEP_MODE_SHUTDOWN = "shutdown"
SLEEP_MODE_HIBERNATE = "hibernate"

# Plugin menu metadata
ui_str = """
<ui>
  <menubar name="tmw-menubar">
    <menu name="Sleep" action="Sleep">
      <placeholder name="ToolsOps_5">
        <menuitem name="SleepConfigure" action="SleepConfigure"/>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""


def human_time(seconds):
	
	if not seconds :
		return seconds;
	"""Return human readable time string from time in seconds"""
	hours = int( math.floor(seconds / 3600.0) )
	seconds = seconds - hours * 3600
	minutes = int( math.floor(seconds / 60.0) )
	seconds = int(seconds - minutes * 60)
	
	time_parts = []
	
	if hours == 1:
		time_parts.append("%d hour" % hours)
	if hours > 1:
		time_parts.append("%d hours" % hours)
	
	if minutes == 1:
		time_parts.append("%d minute" % minutes)
	if minutes > 1:
		time_parts.append("%d minutes" % minutes)
	
	if seconds == 1:
		time_parts.append("%d second" % seconds)
	if seconds > 1:
		time_parts.append("%d seconds" % seconds)
	
	if len(time_parts) == 1:
		time_message = time_parts[0]
	elif len(time_parts) == 2:
		time_message = " and ".join(time_parts)
	else:
		time_message = ", ".join( time_parts[ :-1 ] ) + " and " + time_parts[-1]
	
	return time_message


class SleepPlugin(GObject.Object, Peas.Activatable):

	__gtype_name__ = 'StarterPlugin'
        object = GObject.property (type = GObject.Object)

	"""Main class for plugin"""
	def __init__(self):
		GObject.Object.__init__(self)
		self._totem = None
		
	def do_activate(self):
		self._totem = self.object
		totem_object = self.object
		
		data = dict()
		manager = totem_object.get_ui_manager()
		
		data['action_group'] = Gtk.ActionGroup('Python')
		
		action = Gtk.Action('Sleep', 'Sleep', _('System Shutdown Menu'), None)
		data['action_group'].add_action(action)
		
		action = Gtk.Action('SleepConfigure', _('_Configure'), _("Show Totem's Python console"), 'gnome-mime-text-x-python')
		action.connect('activate', self.show_config, totem_object)
		
		data['action_group'].add_action(action)
		
		manager.insert_action_group(data['action_group'], 0)
		data['ui_id'] = manager.add_ui_from_string(ui_str)
		manager.ensure_update()
		
		totem_object.ShutdownPluginInfo = data
	
	def show_config(self, action, totem_object):
		self.timeout_dialog = TimeoutDialog(totem_object)
		self.watcher = WatcherThread(totem_object, self.timeout_dialog)
		self.config_dialog = ConfigDialog(self.watcher)
		self.config_dialog.show(totem_object)
	
	def do_deactivate(self):
		data = getattr(self._totem,'ShutdownPluginInfo')
        
		manager = self._totem.get_ui_manager()
		manager.remove_ui(data['ui_id'])
		manager.remove_action_group(data['action_group'])
		manager.ensure_update()
		
		self._totem.ShutdownPluginInfo = None
		self._totem = None



class TimeoutDialog:
	"""Dialog that displays warning and time remaining until action with options to take action now or cancel."""
	def __init__(self, totem_object):
		self.totem_object = totem_object
		gladefile = os.path.join( os.path.dirname( os.path.abspath(__file__) ), "timeout.gtk" )
		
		windowname = "window_timeout"
		self.wTree = Gtk.Builder()
		self.wTree.add_from_file(gladefile)

		dic = {	
			"on_button_now_clicked":self.on_clicked_now,
			"on_button_cancel_clicked":self.on_clicked_cancel,
		}
		
		self.wTree.connect_signals(dic)
		
		self.window = self.wTree.get_object(windowname)
		self.label_message = self.wTree.get_object("label_message")
		self.button_now = self.wTree.get_object("button_now")
	
	def show(self):
		mode = getattr(self.totem_object, 'SleepPluginMode')
		self.time = WARNING_TIMEOUT
		
		self.update_time()
		self.button_now.set_label( "%s now" % mode.title() )
		
		self.countdown = CountdownThread(self)
		self.countdown.start()
		
		self.window.show()
	
	def update_time(self):
		mode = getattr(self.totem_object,'SleepPluginMode')
		
		time_message = human_time(self.time)
		
		self.label_message.set_text( "This system will %s in %s." % (mode, time_message) )
	
	def action(self):
		mode = getattr(self.totem_object,'SleepPluginMode')
		self.totem_object.SleepPluginMode = SLEEP_MODE_DISABLED
		
		if mode == SLEEP_MODE_SHUTDOWN:
			# Get the D-Bus session bus
			bus = dbus.SystemBus()
			# Access the Tomboy D-Bus object
			obj = bus.get_object('org.freedesktop.ConsoleKit', '/org/freedesktop/ConsoleKit/Manager')
			
			# Access the Tomboy remote control interface
			powerman = dbus.Interface(obj, "org.freedesktop.ConsoleKit.Manager")
			
			if powerman.CanStop():
				powerman.Stop()
			else :
				print "The system cant shutdown"
		
		elif mode == SLEEP_MODE_HIBERNATE:
			# Get the D-Bus session bus
			bus = dbus.SystemBus()
			# Access the Tomboy D-Bus object
			obj = bus.get_object("org.freedesktop.UPower", "/org/freedesktop/UPower")
			
			
			# Access the Tomboy remote control interface
			powerman = dbus.Interface(obj, "org.freedesktop.UPower")
			
			if powerman.HibernateAllowed():
				powerman.Hibernate()
			else :
				print "The system cant hibernate"
			
				
	
	def on_clicked_now(self, widget):
		if self.countdown.alive:
			self.countdown.terminate()
			self.countdown.join()
		
		self.action()
		self.window.hide()
	
	def on_clicked_cancel(self, widget):
		if self.countdown.alive:
			self.countdown.terminate()
			self.countdown.join()
		
		self.totem_object.SleepPluginMode = SLEEP_MODE_DISABLED
		
		self.window.hide()



class ConfigDialog:
	"""Dialog for enabling and configuring sleep"""
	def __init__(self, watcher):
		self.watcher = watcher
		gladefile = os.path.join( os.path.dirname( os.path.abspath(__file__) ), "sleep.gtk" )
		
		windowname = "window_config"
		self.wTree = Gtk.Builder()
		self.wTree.add_from_file(gladefile)
		
		dic = {	"on_button_ok_clicked":self.on_clicked_ok,
			"on_button_cancel_clicked":self.on_clicked_cancel,
		}
		
		self.wTree.connect_signals(dic)
		
		self.window = self.wTree.get_object(windowname)
		
		self.radio_disabled = self.wTree.get_object("radio_disabled")
		self.radio_shutdown = self.wTree.get_object("radio_shutdown")
		self.radio_hibernate = self.wTree.get_object("radio_hibernate")
	
	def show(self, totem_object):
		self.totem_object = totem_object
		
		mode = getattr(self.totem_object,'SleepPluginMode',None)
		
		if mode == SLEEP_MODE_DISABLED or mode == None:
			self.radio_disabled.set_active(True)
		
		elif mode == SLEEP_MODE_SHUTDOWN:
			self.radio_shutdown.set_active(True)
		
		elif mode == SLEEP_MODE_HIBERNATE:
			self.radio_hibernate.set_active(True)
		
		self.window.show()
	
	def on_clicked_ok(self, widget):
		
		if self.watcher.alive:
			self.watcher.terminate()
			self.watcher.join()
		
		if self.radio_disabled.get_active():
			self.totem_object.SleepPluginMode = SLEEP_MODE_DISABLED
		else:
			if self.radio_shutdown.get_active():
				self.totem_object.SleepPluginMode = SLEEP_MODE_SHUTDOWN
		
			elif self.radio_hibernate.get_active():
				self.totem_object.SleepPluginMode = SLEEP_MODE_HIBERNATE
				
			if self.watcher.alive:
				print "error, still there"
			
			self.watcher.start()
		
		self.window.hide()
	
	def on_clicked_cancel(self, widget):
		self.window.hide()



class WatcherThread(threading.Thread):
	"""Watches the Totom play state and displayes timeout dialog when Totem is in a known finished playing state"""
	alive = False
	
	def __init__(self, totem_object, timeout_dialog):
		self.totem_object = totem_object
		self.timeout_dialog = timeout_dialog
		
		threading.Thread.__init__(self)
	
	def run(self):
		self.alive = True
		while not  self.totem_object.get_playlist_length() :
			time.sleep(POLLING_PERIOD)
			
		while self.alive:
			
			# If we are playing a DVD then we can't simply check that that playback has finished because 
			# Totem will return to the menu which will loop. The time will however go beyond the length so
			# we can detect this using this method. TODO need to test this with various DVDs.
			
			if self.totem_object.get_current_mrl() and self.totem_object.get_current_mrl().startswith("dvd://"):
				video_playing = self.totem_object.get_property("current-time") <= self.totem_object.get_property("stream-length")
			else:
				video_playing = self.totem_object.is_playing()
			
			# If the video is not playing then shown the TimeoutDialog and finish this thread.
			if not video_playing:
				self.alive = False
				self.timeout_dialog.show()
				break
			
			time.sleep(POLLING_PERIOD)
		return;
		
	def terminate(self):
		self.alive = False



class CountdownThread(threading.Thread):
	"""Updates time remaining in TimeoutDialog and calls action when time reaches zero."""
	def __init__(self, parent):
		self.parent = parent
		self.alive = True
		
		threading.Thread.__init__(self)
	
	def run(self):
		while self.alive:
			time.sleep(1)
			self.parent.time -= 1
			self.parent.update_time()
			if self.parent.time <= 0:
				self.alive = False
				self.parent.window.hide()
				self.parent.action()
	
	def terminate(self):
		self.alive = False