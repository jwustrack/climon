# climon

== Configuration ==

It's probably pretty self-explanatory:
   
  [common]
  database=climon.db
  port=8765
  monitor-interval=60
  
  [sensor:living-room]
  name=Living room
  type=DHT11
  source=4

  [sensor:living-room-remote]
  name=Living room (black)
  type=climon
  source=http://192.168.1.102:8765/sensor/living-room
  color=#0033ff


== Running ==

  $ climon.sh <start|stop|restart>
