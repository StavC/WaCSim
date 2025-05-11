############################
Network Event Config Options
############################

.. contents:: Table of Contents
   :depth: 4
   :local:

*********************
Common Config Options
*********************

Events differ from attacks in that no packets are captured and modified by some malicious actor, and are instead caused by some malfunction. This means that no ARP posioning attack occurs, and no signature of an attack will appear in PCAP files. In the current version, events are able to cause network losses and/or network delays temporarily based on the trigger conditions of the event.

name
----
**(Required Option)**

**Takes:** string of any length/characters excluding ``(space)`` and ``-`` characters.

The name of the event is used for the .CSV file labels, but has no effect otherwise.

trigger
-------
**(Required Option for All Attacks)**

**Takes:** a schema that determines when the event is triggered.

The trigger option is a container that contains the options for how an event is triggered and when. Overall, there are three different types of triggers available in WaCSim, with their options to determine their behavior. These tree types are `time`, `below` and `above`, and `between.`

time
~~~~
The time trigger type simply starts and ends an event based on the current iteration number of the simulation.

Example:

.. code-block:: yaml

	trigger:
		type: time
		start: 10
		end: 30
		
The event will begin on the iteration specified by `start`. Similarly, the value of `end` will be the iteration in which the event will no longer affect the system.

below or above
~~~~~~~~~~~~~~
The `below` or `above` trigger types differ from `time` in that the event no longer occurs during a fixed time in the simulation, and can activate and deactivate multiple times throughout a simulation.

Example

.. code-block:: yaml

	trigger:
		type: below
		sensor: T41
		value: 4

In the example, whenever the tank T41 measures a level in meters below 4, the event will begin. Then, if the T41 value ever goes above 4 again, the event will stop.

between
~~~~~~~
The `between` trigger is essentially the same as below or above, where the event will only start when the value of a sensor is between two values.

Example

.. code-block:: yaml

	trigger:
		type: between
		sensor: T41
		lower_value: 2
		upper_value: 4

In the example, whenever the tank T41 measures a level in meters between 2 and 4, the event will start. Then, if the T41 value ever moves out of this range, the event will stop.

type
----
**(Required Option for Network Events)**

**Takes:** ``packet_loss``, ``network_delay``, ``network_delay_loss``.

Currently, the event types available mimic the behavior from ``network_delay_data`` and ``network_loss_data`` from the `Experiment Config Docs`_. The main difference is that using network events allows one to have specific triggers that cause the netwrok delay and/or loss, while the two options from the experiment config docs are always active.

packet_loss
~~~~~~~~~~~
The ``packet_loss`` network event type mimics the behavior of ``network_loss_data``. ``value`` is used to determine the % chance (from 0-100%) that an individual packet, inbound or outbound, is dropped for the targeted PLC.

.. code-block:: yaml

   network_events:
     - name: plc1network_event_loss
       type: packet_loss
       target: PLC1
       value: 20
       trigger:
         type: time
         start: 200
         end: 250
		 
packet_delay
~~~~~~~~~~~
The ``packet_delay`` network event type mimics the behavior of ``network_delay_data``. ``value`` is used to determine the delay in milliseconds that an individual packet, inbound or outbound, of the targeted PLC recieves. 

.. code-block:: yaml

   network_events:
     - name: plc1network_event_delay
       type: packet_delay
       target: PLC1
       value: 5
       trigger:
         type: time
         start: 200
         end: 250
		 
network_delay_loss
~~~~~~~~~~~
The ``packet_loss`` network event type mimics the behavior of both ``network_loss_data`` and ``network_delay_loss``.  Instead of ``value``, ``loss_value`` and ``delay_value`` are used, which behave in the same way as ``value`` does for their respective network event type.

.. code-block:: yaml

   network_events:
     - name: plc1network_event_delayloss
       type: packet_delay_loss
       target: PLC1
       loss_value: 20
	   delay_value: 5
       trigger:
         type: time
         start: 200
         end: 250
target
------
**(Required Option for Network Events)**

**Takes:** string representing name of target PLC.

value
-----
**(Required Option for** ``network_loss`` **and** ``network_delay`` **)**

**Takes:** integer representing event value.

The meaning of ``value`` depends on the event type. For ``network_loss`` it represents the % chance (from 0-100%) that an individual packet is dropped, and for ``network_delay`` it represents the delay a packet recieves in milliseconds.

loss_value
----------
**(Required for** ``network_delay_loss`` **)**

**Takes:** integer representing loss value.

This option is only used when the event ``type`` is ``network_delay_loss`` and represents the % chance (from 0-100%) that an individual packet is dropped.

delay_value
-----------
**(Required for** ``network_delay_loss`` **)**

**Takes:** integer representing delay value.

This option is only used when the event ``type`` is ``network_delay_loss`` and represents the network delay in milliseconds.

.. _`Experiment Config Docs`: experiment_config_docs.rst
