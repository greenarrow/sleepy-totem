sleepy-totem
--

Plugin for Totem movie player that can shutdown or hibernate the computer when the playlist finishes.

In order to shutdown the computer, ConsoleKit is required. You can install it via apt on Debian-based distributions:

```
 # apt-get install consolekit
```

To install in your home directory just run:

    $ chmod u+x install.sh 
    $ ./install.sh

Start Totem and open the plugin dialog from the Edit->Plugins menu
Enable "Sleepy Totem"

A new menu "Sleep" should now be added to Totem. It takes immediate effect (for now).

TODO

- [x] Fix thread joining to allow stopping sleep mode and starting again (from either pre or post timeout dialog)
- [x] Prevent events from firing up if playlist is empty
- [x] Turn choice into a setting to be used afterwards instead of taking immediate effect
- [ ] Get some nice tickable gtk menus
- [ ] Move timeout to config box
- [x] Write README
