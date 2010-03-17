import totem
import gobject, gtk, gtk.glade
import os, threading, time, dbus

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

SLEEP_MODE_DISABLED = "disabled"
SLEEP_MODE_SHUTDOWN = "shutdown"
SLEEP_MODE_HIBERNATE = "hibernate"

POLLING_PERIOD = 5
WARNING_TIMEOUT = 120

TESTING = True

class WatcherThread(threading.Thread):
	alive = False
	
	def __init__(self, totem_object, timeout_dialog):
		self.totem_object = totem_object
		self.timeout_dialog = timeout_dialog
		
		threading.Thread.__init__(self)
	
	def run(self):
		self.alive = True
		while self.alive:
			#print "checking"
			
			if not self.totem_object.is_playing():
				self.alive = False
				self.timeout_dialog.show()
				break
			
			time.sleep(POLLING_PERIOD)
	
	def terminate(self):
		self.alive = False
	


class CountDown(threading.Thread):
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

class TimeoutDialog:
	
	def __init__(self, totem_object):
		self.totem_object = totem_object
		gladefile = os.path.join( os.path.dirname( os.path.abspath(__file__) ), "sleep.glade" )
		
		windowname = "window_timeout"
		self.wTree = gtk.glade.XML(gladefile,windowname)
		
		dic = {	"on_button_now_clicked":self.on_clicked_now,
			"on_button_cancel_clicked":self.on_clicked_cancel,
		}
		
		self.wTree.signal_autoconnect(dic)
		
		self.window = self.wTree.get_widget(windowname)
		self.label_message = self.wTree.get_widget("label_message")
		self.button_now = self.wTree.get_widget("button_now")
	
	def show(self):
		mode = self.totem_object.get_data('SleepPluginMode')
		self.time = WARNING_TIMEOUT
		
		self.update_time()
		self.button_now.set_label( "%s now" % mode.title() )
		
		self.countdown = CountDown(self)
		self.countdown.start()
		
		self.window.show()
	
	def update_time(self):
		mode = self.totem_object.get_data('SleepPluginMode')
		time_message = "%d seconds" % self.time
		if self.time >= 60:
			time_message = "%d minutes" % int( round(self.time / 60.0) )
		
		self.label_message.set_text( "This system will %s in %s." % (mode, time_message) )
	
	def action(self):
		mode = self.totem_object.get_data('SleepPluginMode')
		if mode == SLEEP_MODE_SHUTDOWN:
			print "todo shutdown"
		
		elif mode == SLEEP_MODE_HIBERNATE:
			if TESTING:
				print "TEST MODE: We would hibernate here. zzzzz."
			else:
				# Get the D-Bus session bus
				bus = dbus.SessionBus()
				# Access the Tomboy D-Bus object
				obj = bus.get_object("org.freedesktop.PowerManagement", "/org/freedesktop/PowerManagement")
				# Access the Tomboy remote control interface
				powerman = dbus.Interface(obj, "org.freedesktop.PowerManagement")
				powerman.Hibernate()
	
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
		
		self.window.hide()

class ConfigDialog:
	
	def __init__(self, watcher):
		self.watcher = watcher
		gladefile = os.path.join( os.path.dirname( os.path.abspath(__file__) ), "sleep.glade" )
		
		windowname = "window_config"
		self.wTree = gtk.glade.XML(gladefile,windowname)
		
		dic = {	"on_button_ok_clicked":self.on_clicked_ok,
			"on_button_cancel_clicked":self.on_clicked_cancel,
		}
		
		self.wTree.signal_autoconnect(dic)
		
		self.window = self.wTree.get_widget(windowname)
		
		self.radio_disabled = self.wTree.get_widget("radio_disabled")
		self.radio_shutdown = self.wTree.get_widget("radio_shutdown")
		self.radio_hibernate = self.wTree.get_widget("radio_hibernate")
	
	def show(self, totem_object):
		self.totem_object = totem_object
		
		mode = totem_object.get_data('SleepPluginMode')
		if mode == SLEEP_MODE_DISABLED or mode == None:
			self.radio_disabled.set_active(True)
		
		elif mode == SLEEP_MODE_SHUTDOWN:
			self.radio_shutdown.set_active(True)
		
		elif mode == SLEEP_MODE_HIBERNATE:
			self.radio_hibernate.set_active(True)
		
		self.window.show()
	
	def on_clicked_ok(self, widget):
		
		if self.radio_disabled.get_active():
			self.totem_object.set_data('SleepPluginMode', SLEEP_MODE_DISABLED)
			if self.watcher.alive:
				self.watcher.terminate()
				self.watcher.join()
		else:
			if self.radio_shutdown.get_active():
				self.totem_object.set_data('SleepPluginMode', SLEEP_MODE_SHUTDOWN)
		
			elif self.radio_hibernate.get_active():
				self.totem_object.set_data('SleepPluginMode', SLEEP_MODE_HIBERNATE)
				
			if self.watcher.alive:
				print "error, still there"
			
			#print "start watcher"
			self.watcher.start()
		
		self.window.hide()
	
	
	def on_clicked_cancel(self, widget):
		#print "cancel"
		self.window.hide()

class SleepPlugin(totem.Plugin):

	def __init__(self):
		totem.Plugin.__init__(self)

	def activate(self, totem_object):
		#print "Activating sample Python plugin"
		#totem.action_fullscreen_toggle()
		
		data = dict()
		manager = totem_object.get_ui_manager()

		data['action_group'] = gtk.ActionGroup('Python')
		
		action = gtk.Action('Sleep', 'Sleep', _('System Shutdown Menu'), None)
		data['action_group'].add_action(action)

		action = gtk.Action('SleepConfigure', _('_Configure'),
		                    _("Show Totem's Python console"),
		                    'gnome-mime-text-x-python')
		action.connect('activate', self.show_config, totem_object)
		# make this a tickable
		data['action_group'].add_action(action)

		
		manager.insert_action_group(data['action_group'], 0)
		data['ui_id'] = manager.add_ui_from_string(ui_str)
		manager.ensure_update()
		
		totem_object.set_data('ShutdownPluginInfo', data)
		
		self.timeout_dialog = TimeoutDialog(totem_object)
		self.watcher = WatcherThread(totem_object, self.timeout_dialog)
		self.config_dialog = ConfigDialog(self.watcher)
		
		
	
	def show_config(self, action, totem_object):
		self.config_dialog.show(totem_object)
		#self.timeout_dialog.show(totem_object)
	
	def deactivate(self, totem_object):
		#print "Deactivating sample Python plugin"
		
		data = totem_object.get_data('ShutdownPluginInfo')

		manager = totem_object.get_ui_manager()
		manager.remove_ui(data['ui_id'])
		manager.remove_action_group(data['action_group'])
		manager.ensure_update()

		totem_object.set_data('ShutdownPluginInfo', None)
		
		#if self.window is not None:
		#	self.window.destroy()





