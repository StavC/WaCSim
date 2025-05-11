#####################
Attack Config Options
#####################

.. contents:: Table of Contents
   :depth: 4
   :local:

*********************
Common Config Options
*********************
   
name
----
**(Required Option for All Attacks)**

**Takes:** a string of any length and characters, excluding spaces and hyphens.

The attack name is used for CSV file labels but has no other effect.

trigger
-------
**(Required Option for All Attacks)**

**Takes:** a schema that determines when the attack is triggered.

The **trigger** option is a container for the parameters that define how and when an attack is initiated. There are three types of triggers available in WaCSim: ``time``, ``below``/``above``, and ``between``.

time
~~~~
The ``time`` trigger starts and stops an attack based on the simulation’s current iteration number.

.. code-block:: yaml

   trigger:
     type: time
     start: 10
     end: 30

In this example, the attack begins at the start of iteration ``10`` and remains active until the end of iteration ``30``.

below or above
~~~~~~~~~~~~~~
The ``below`` and ``above`` triggers differ from ``time`` in that the attack is not confined to a fixed period. Instead, the attack can activate and deactivate multiple times.

.. code-block:: yaml

   trigger:
     type: below
     sensor: T41
     value: 4

Here, whenever tank T41 measures a level below 4 meters, the attack is initiated. If the value rises above 4 again, the attack stops at the end of that iteration.

*Note:* For ``below``/``above`` triggers, the attacker actively polls the specified sensor, so these requests will appear unobfuscated in the PCAP file for the associated PLC.

between
~~~~~~~
The ``between`` trigger operates similarly to ``below``/``above``, but the attack is activated only when a sensor’s value is between two specified thresholds. The attack stops at the end of an iteration when the value moves outside that range.

.. code-block:: yaml

   trigger:
     type: between
     sensor: T41
     lower_value: 2
     upper_value: 4

In this example, the attack is activated if tank T41’s level is between 2 and 4 meters and stops once the value falls outside that range.

*********************
Device Attack Options
*********************

actuator
--------
**(Required Option for Device Attacks)**

**Takes:** a string representing the actuator name.

The actuator name should match the pump or valve defined in the INP file. This is the device that the attack targets.

command
-------
**(Required Option for Device Attacks)**

**Takes:** ``open``, ``closed``, or an integer representing a pump speed multiplier.

The ``command`` attribute determines the action taken once the attack trigger condition is met. When set to ``open`` or ``closed``, the actuator’s status is changed for the duration of the attack, regardless of commands from the SCADA or PLC. When set to an integer, it acts as a multiplier for the pump’s baseline speed (e.g., a value of ``1.5`` increases the pump speed by 1.5×).

**Note:** Pump speed modification only works when using the epynet simulator.

**********************
Network Attack Options
**********************

type
----
**(Required Option for Network Attacks)**

**Takes:** ``naive_mitm``, ``mitm``, ``server_mitm``, ``concealment_mitm``, ``unconstrained_blackbox_concealment_mitm``, ``replay_mitm``, or ``simple_dos``.

The attack type determines the underlying mechanism. Currently, there are two primary categories: man-in-the-middle (MitM) attacks and denial-of-service (DoS) attacks.

naive_mitm
~~~~~~~~~~
The ``naive_mitm`` attack is the simplest form of man-in-the-middle attack. The attacker launches an ARP poisoning attack to position itself between the switch and PLC, intercepting all packets (from either the PLC or other PLCs, depending on the ``direction`` parameter) and modifying them using the provided ``value`` or ``offset``. It is termed “naive” because it modifies every intercepted tag without concealing its actions.

.. code-block:: yaml

   network_attacks:
     - name: plc1attack_naive
       type: naive_mitm
       target: PLC1
       offset: 7.0
       trigger:
         type: time
         start: 200
         end: 250

mitm
~~~~
The ``mitm`` attack is the standard man-in-the-middle variant. After performing ARP poisoning to insert itself between the switch and PLC, the attacker intercepts all packets and selectively modifies only specified tags, regardless of if they are inbound or outbound packets, using either a ``value`` or ``offset`` parameter. This makes the ``mitm`` attack more targeted than the naive MitM variant.

.. code-block:: yaml

   network_attacks:
     - name: plc1attack_mitm
       type: mitm
       target: PLC1
       tags:
         - tag: T41
           value: 1
       trigger:
         type: time
         start: 200
         end: 250

server_mitm
~~~~~~~~~~~
The ``server_mitm`` attack is an alternative to the standard MitM. Like other MitM attacks, it begins with an ARP poisoning attack. It then sets up a CPPPO server to respond to requests for the targeted PLC. Unlike other MitM variants, the ``server_mitm`` attack only modifies packets originating from the targeted PLC.

.. code-block:: yaml

   network_attacks:
     - name: plc1attack_server_mitm
       type: server_mitm
       target: PLC1
       tags:
         - tag: T41
           value: 1
       trigger:
         type: time
         start: 200
         end: 250

replay_mitm
~~~~~~~~~~~
The ``replay_mitm`` attack does not modify packets. Instead, after an initial ARP poisoning attack, the attacker captures packets from the PLC to the SCADA over a specified interval (using ``capture_start`` and ``capture_end``) and later replays them starting at the iteration defined by ``replay_start``.

.. code-block:: yaml

   network_attacks:
     - name: plc1attack_replay_mitm
       type: replay_mitm
       target: PLC1
       capture_start: 50
       capture_end: 100
       replay_start: 150

concealment_mitm
~~~~~~~~~~~~~~~~~
The ``concealment_mitm`` attack is similar to the standard MitM but includes options to conceal its actions from the SCADA. After ARP poisoning, the attacker intercepts and modifies packets going to or from the targeted PLC based on specified tags. Additionally, using the ``concealment_data`` option, the attacker can provide alternative values for packets sent to the SCADA from the targeted PLC.

.. code-block:: yaml

   network_attacks:
     - name: plc1attack_concealment_mitm
       type: concealment_mitm
       target: PLC1
       tags:
         - tag: T41
           value: 1
       concealment_data:
         type: value
         concealment_value:
           - tag: T41
             value: 5
       trigger:
         type: time
         start: 200
         end: 250

seq_mitm
~~~~~~~~~~~~~~~~~
The ``seq_mitm`` attack allows for progressive changes in the offset or value of an attack in time. Two exclusive parameters are used for this attack, ``scaleParam`` and ``scaleTime``. ``scaleParam`` is an additive/subtractive amount that changes the initial offset/value provided for the attack each time the scale is changed. ``scaletime`` determines how often ``scaleParam`` modifies the attack offset/value, measured in iterations of the simulation. For example, if an initial ``offset`` of ``0.5``, ``scaleParam`` of ``0.1`` and ``scaleTime`` of ``3`` is given then by the sixth iteration of the attack the offset will be ``0.7`` instead of ``0.5``.

.. code-block:: yaml

   network_attacks:
     - name: plc1attack_concealment_mitm
       type: concealment_mitm
       target: PLC1
       tags:
         - tag: T41
           offset: 1
           scaleParam: 0.5
           scaleTime: 2
       trigger:
         type: time
         start: 200
         end: 250

simple_dos
~~~~~~~~~
The ``simple_dos`` attack is a denial-of-service attack that prevents packets from reaching their destination. After launching an ARP poisoning attack similar to MitM methods, the attacker intercepts packets and deliberately does not forward them.  
- If ``direction`` is set to ``destination``, packets from other PLCs will not reach the targeted PLC.  
- If ``direction`` is set to ``source``, packets from the targeted PLC will not reach other PLCs.

unconstrained_blackbox_concealment_mitm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This attack is specific to the CTown network. For details on its operation and purpose, refer to `the paper`_ and the original `WaCSim documentation`_.

target
------
**(Required Option for Network Attacks)**

**Takes:** a string representing the name of the target PLC.

The targeted PLC depends on the attack type and sometimes the ``direction`` parameter. For attacks such as ``server_mitm``, ``replay_mitm``, and the concealment portion of ``concealment_mitm``, the target is the PLC whose local sensors include the tag(s) to be modified (i.e., the ``source``). In contrast, the ``mitm`` attack and attack portion of ``concealment_mitm`` are able to target both inbound and outbound packets. The behavior of ``naive_mitm`` and ``simple_dos`` depends on the specified ``direction``.

direction
---------
**Available to:** ``naive_mitm``, ``simple_dos``.

**Takes:** ``source`` **or** ``destination`` **(Default:** ``source`` **)**

This parameter determines whether an attack affects outbound packets from the targeted PLC (``source``) or inbound packets to the targeted PLC (``destination``).

tags
----
**(Required for** ``mitm`` **,** ``server_mitm`` **,** **and** ``concealment_mitm`` **attacks)**

**Available to:** ``mitm``, ``server_mitm``, ``concealment_mitm``.

**Takes:** a schema defining the tags to be modified.

The **tags** option acts as a container for one or more tag modification entries. For each tag, the modification can be specified using either ``value`` or ``offset``.

.. code-block:: yaml

   tags:
     - tag: T41
       value: 10
     - tag: T42
       offset: 5

tag
~~~
**(Required)**

**Takes:** a string representing the targeted tag name.

concealment_data
----------------
**(Required for** ``concealment_mitm`` **attacks)**

**Available to:** ``concealment_mitm``.

Concealment data defines how the attack is hidden from the SCADA. It only applies to data from the targeted PLC that is sent to the SCADA, while other PLCs receive the modified data as specified by the attack parameters.

type
~~~~
**(Required)**

**Takes:** ``path``, ``value``, ``payload_replay``, or ``network_replay``.

path
^^^^
Setting ``type`` to ``path`` uses a CSV file to provide concealment data. The CSV should include a column header named ``Iteration`` followed by tag names, with each row containing the iteration number and the corresponding concealment values.

.. code-block:: yaml

   concealment_data:
     type: path
     path: T41_concealment_data.csv
	 
.. list-table:: Example CSV
   :widths: 25 25 50
   :header-rows: 1

   * - Iteration
     - T41
   * - 1
     - 5
   * - 7
     - 6
   * - 10
     - 7

value
^^^^^
When ``type`` is set to ``value``, concealment is achieved by specifying tag modifications (using ``value`` or ``offset``) for the data sent to the SCADA.

.. code-block:: yaml

   concealment_data:
     type: value
     concealment_value:
       - tag: T41
         value: 5

payload_replay
^^^^^^^^^^^^^^
With ``payload_replay``, the attack first captures specific tag values over a duration (using ``capture_start`` and ``capture_end``), then replays these values starting at the iteration defined by ``replay_start``. This method replays only tag values rather than entire packets. Additionally, when using ``payload_replay`` the actual attack will not begin until the iteration specified by ``replay_start``. This ensures that the attacker does not attack unconcealed.

.. code-block:: yaml

   concealment_data:
     type: payload_replay
     capture_start: 50
     capture_end: 100
     replay_start: 150

network_replay
^^^^^^^^^^^^^^
When set to ``network_replay``, concealment is performed by capturing all packets over a defined period (using ``capture_start`` and ``capture_end``) and then replaying them starting at ``replay_start``, similar to the ``replay_mitm`` attack. Additionally, when using ``network_replay`` the actual attack will not begin until the iteration specified by ``replay_start``. This ensures that the attacker does not attack unconcealed.

.. code-block:: yaml

   concealment_data:
     type: network_replay
     capture_start: 50
     capture_end: 100
     replay_start: 150

value
-----
**Available to:** ``mitm``, ``server_mitm``, ``concealment_mitm``.

**Takes:** a float number representing the attack value or a path to a CSV file containg attack values.

This parameter is used in all MitM attacks (except ``naive_mitm`` and ``replay_mitm``) and for concealment data when using the ``value`` method. It forces the tag value to equal the specified number.

offset
------
**Available to:** ``mitm``, ``server_mitm``, ``concealment_mitm``.

**Takes:** a float number representing the attack value.

Used similarly to ``value``, the ``offset`` parameter is applied in MitM attacks (except ``naive_mitm`` and ``replay_mitm``) and for concealment data when using the ``value`` method. The tag value is modified as follows:
``final_value = original_value + offset``

The offset may be positive or negative.

scaleParam
----------
**(Required for** ``seq_mitm`` **attacks)**

**Available to:** ``seq_mitm``.

**Takes:** a float number representing the scale value.

Determines how much the value/offset of the attack changes with each sequential increase/decrease.

The value may be positive or negative.

scaleTime
---------
**(Required for** ``seq_mitm`` **attacks)**

**Available to:** ``seq_mitm``.

**Takes:** an integer representing how often the scale of the attack should change.

Determines how often, in units of simulation iterations, the value should change during a sequential MitM attack.

capture_start
-------------
**(Required for** ``replay_mitm``, **attacks)**

**Available to:** ``replay``, ``concealment_mitm``.

**Takes:** an integer representing the iteration at which to begin capturing packets or payloads.

This parameter marks the start of the capture period for packets (in ``replay_mitm`` and ``network_replay``) or payloads (in ``payload_replay``).

capture_end
-----------
**(Required for** ``replay_mitm`` **attacks)**

**Available to:** ``replay``, ``concealment_mitm``.

**Takes:** an integer representing the iteration at which to stop capturing packets or payloads.

Data from the iteration specified by ``end_capture`` is included in the capture; only data from subsequent iterations is excluded.

replay_start
------------
**(Required for** ``replay_mitm`` **attacks)**

**Available to:** ``replay``, ``concealment_mitm``.

**Takes:** an integer representing the iteration at which to start replaying captured packets or payloads.

Captured data is replayed iteratively starting from this iteration until all captured data is sent. The replay duration matches the capture duration.

.. _`from the paper`: https://dl.acm.org/doi/10.1145/3564625.3564633
.. _`WaCSim documentation`: https://github.com/StavC/WaCSim/blob/master/doc/attacks.rst#unconstrained-blackbox-concealment-mitm-attack
