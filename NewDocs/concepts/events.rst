.. B.5 Events
.. WaCSim User Manual

========================================
Events
========================================

Events model **non-malicious** network effects: delay and packet loss on links. Unlike attacks, no actor captures or modifies packets and no ARP poisoning is used—events are applied at a switch link using Linux ``tc`` (traffic control). They are useful for simulating faulty or congested links, or for testing how control logic behaves under loss or delay. Events are defined in a **separate YAML file** and referenced from the main config with ``events: !include <file>.yaml``.

----------------------------------------
How events fit in
----------------------------------------

- When you set ``events: !include my_events.yaml``, WaCSim loads that file. It must contain **``network_events``** (a list).
- Each **network event** runs as a separate process and applies delay and/or loss on the link to the **target** PLC (or SCADA) when the event’s **trigger** is active.
- When the trigger is not satisfied, the event is inactive (no delay or loss). So you can model temporary link degradation (e.g. between iterations 50 and 100, or when a tank level is below a threshold).
- Events do not appear in PCAPs as “attacks”; they only change link behaviour (delay/loss) on the target’s interface.

----------------------------------------
Config file structure
----------------------------------------

The included events file has this shape:

.. code-block:: yaml

   network_events:
     - name: plc1_loss
       type: packet_loss
       target: PLC1
       value: 15
       trigger:
         type: time
         start: 50
         end: 120
     - name: plc2_delay
       type: network_delay
       target: PLC2
       value: 10
       trigger:
         type: time
         start: 30
         end: 80

Paths inside the events file are relative to the **main config file** directory (if you use any file references).

----------------------------------------
Event types
----------------------------------------

**packet_loss**
  Drops a percentage of packets on the link to the **target**. **``value``** is the loss rate in percent (0–100). For example, ``value: 20`` means 20% of packets are dropped while the event is active. Implemented via Linux ``tc netem loss``.

**network_delay**
  Delays every packet on the link to the **target** by a fixed amount. **``value``** is the delay in **milliseconds**. For example, ``value: 10`` means each packet is delayed by 10 ms. Implemented via Linux ``tc netem delay``.

**network_delay_loss**
  Applies both delay and loss on the link. Use **``loss_value``** (percent, 0–100) and **``delay_value``** (milliseconds) instead of ``value``. Useful when you want a single event to model both effects (e.g. 5% loss and 20 ms delay).

----------------------------------------
Common options
----------------------------------------

**name** (required)
  A unique label for the event (used in logs and CSV output). No spaces or hyphens; use letters, numbers, underscores. Length 1–20 characters.

**target** (required)
  The **PLC name** (e.g. ``PLC1``, ``PLC4``) or **``scada``** that this event targets. Delay/loss are applied on the link to that node.

**trigger** (required)
  When the event is active. Same schema as for attacks:

  - **``time``** — Active from iteration ``start`` through ``end`` (inclusive).

    .. code-block:: yaml

       trigger:
         type: time
         start: 10
         end: 30

  - **``below`` / ``above``** — Active when the given sensor is below (or above) a value. Can turn on and off as the sensor value crosses the threshold.

    .. code-block:: yaml

       trigger:
         type: below
         sensor: T41
         value: 4

  - **``between``** — Active when the sensor value is between ``lower_value`` and ``upper_value``.

    .. code-block:: yaml

       trigger:
         type: between
         sensor: T41
         lower_value: 2
         upper_value: 4

  The sensor name must match a tag that the target PLC (or the network) can provide.

**value** (required for ``packet_loss`` and ``network_delay``)
  - For **packet_loss**: loss rate in percent (0–100).
  - For **network_delay**: delay in milliseconds.

**loss_value** and **delay_value** (required for ``network_delay_loss``)
  - **loss_value**: loss rate in percent (0–100).
  - **delay_value**: delay in milliseconds.

----------------------------------------
Events vs. always-on loss/delay data
----------------------------------------

The main config can also set **``network_loss_data``**, **``network_delay_data``**, and **``network_jitter_data``** to paths to CSV files. Those options define **always-on** (or batch-specific) loss/delay/jitter per link for the whole run: column headers are typically ``scada`` and PLC names, and each row gives values for one simulation (or one batch run). There is no trigger—the values apply from the start.

**Network events** instead apply delay/loss only when their **trigger** is satisfied. So you can model “link degrades between iterations 50 and 100” or “loss when tank T41 is below 3 m” without changing the main config CSV. Use events when you need **time- or condition-dependent** link effects; use the CSV options when you want **fixed** loss/delay (or batch-varying) for the entire run.

----------------------------------------
Examples
----------------------------------------

**Packet loss for 50 iterations:**

.. code-block:: yaml

   network_events:
     - name: plc3_loss
       type: packet_loss
       target: PLC3
       value: 25
       trigger:
         type: time
         start: 100
         end: 150

**Delay and loss together:**

.. code-block:: yaml

   network_events:
     - name: plc2_delay_loss
       type: network_delay_loss
       target: PLC2
       loss_value: 10
       delay_value: 15
       trigger:
         type: time
         start: 20
         end: 80

----------------------------------------
Where event configs live
----------------------------------------

- Create a YAML file (e.g. ``my_events.yaml``) in the **same directory** as your main config (or in a subdirectory; paths are relative to the main config directory).
- Put **``network_events``** at the top level with a list of events.
- In the main config: ``events: !include my_events.yaml``.
- You can have multiple events in one file. Each event runs as its own process and applies to the target’s link when its trigger is active.
