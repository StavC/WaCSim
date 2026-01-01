#!/usr/bin/env python3
"""
WaCSim Visualization Script - DoS Attack Analysis
Generates plots comparing DoS attack scenarios with and without guardrail protection.

Usage:
    python run_visualization.py
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

# Create output directory
os.makedirs('ScadaCaseNew', exist_ok=True)

print("=" * 60)
print("WaCSim DoS Attack Visualization")
print("=" * 60)

# ============================================
# Helper Functions
# ============================================

def find_attack_intervals(data, flag_column):
    """Find start and end iterations of attacks based on flag column."""
    attack_intervals = []
    attack_start = None

    for index, flag in enumerate(data[flag_column]):
        if flag == 1 and attack_start is None:
            attack_start = data['iteration'].iloc[index]
        elif flag == 0 and attack_start is not None:
            attack_end = data['iteration'].iloc[index]
            attack_intervals.append((attack_start, attack_end))
            attack_start = None

    return attack_intervals

def adjust_ylim(ax, columns, df, min_override=None, legend_space=0.25):
    """Increase y-limit dynamically to create more space for the legend at top."""
    min_val = df[columns].min().min()
    min_val = min_val if min_val <= 0 else 0
    if min_override is not None:
        min_val = min_override
    max_val = df[columns].max().max()
    data_range = max_val - min_val
    # Add space at top for legend
    ax.set_ylim(min_val - data_range * 0.05, max_val + data_range * legend_space)

def add_legend_top_center(ax):
    """Add legend at top center, outside the plot area."""
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.12), ncol=3, frameon=True, 
              fancybox=True, framealpha=0.95, fontsize=10)
    ax.tick_params(axis='both', labelsize=11)

# ============================================
# 0. Cyber Layer - Packet Analysis (PCAP)
# ============================================
print("\n[0/4] Generating Cyber Layer - Packet Analysis plot...")

try:
    from scapy.all import rdpcap, TCP
    import seaborn as sns
    sns.set_theme(style="whitegrid")
    
    def classify_packet_detailed(packet):
        """Classify packet with TCP flag details."""
        if packet.haslayer("ARP"):
            return "ARP"
        elif packet.haslayer("TCP"):
            tcp = packet["TCP"]
            flags = str(tcp.flags)
            if 'S' in flags and 'A' not in flags:
                return "TCP-SYN"  # SYN only (connection attempt)
            elif 'P' in flags:
                return "TCP-DATA"  # Push flag = data transfer
            else:
                return "TCP-OTHER"
        elif packet.haslayer("ICMP"):
            return "ICMP"
        elif packet.haslayer("UDP"):
            return "UDP"
        else:
            return "Other"

    def process_pcap_detailed(file_path):
        """Process pcap file with detailed TCP classification."""
        packets = rdpcap(file_path)
        packet_times = {}

        for packet in packets:
            packet_type = classify_packet_detailed(packet)
            packet_time = datetime.fromtimestamp(float(packet.time))

            if packet_type not in packet_times:
                packet_times[packet_type] = []

            packet_times[packet_type].append(packet_time)

        return packet_times

    # Load pcap files - All PLCs, Attacker, SCADA
    base_path = '../examples/EdenTown/Scada_Case/3_DoS_WithGuard/outputNew3/'
    
    packet_times_plc1 = process_pcap_detailed(base_path + 'PLC1-eth0.pcap')
    packet_times_plc2 = process_pcap_detailed(base_path + 'PLC2-eth0.pcap')
    packet_times_plc3 = process_pcap_detailed(base_path + 'PLC3-eth0.pcap')
    packet_times_plc4 = process_pcap_detailed(base_path + 'PLC4-eth0.pcap')
    packet_times_attacker = process_pcap_detailed(base_path + 'plc2Attac-eth0.pcap')
    packet_times_scada = process_pcap_detailed(base_path + 'scada-eth0.pcap')

    # Gather all timestamps to determine global min and max
    all_times = []
    for pt_dict in [packet_times_plc1, packet_times_plc2, packet_times_plc3, packet_times_plc4, packet_times_attacker, packet_times_scada]:
        for times in pt_dict.values():
            all_times.extend(times)

    bin_size = 15  # seconds (larger = smoother)
    global_min_time = min(all_times)
    global_max_time = max(all_times)

    # Create global bins
    bins = np.arange(global_min_time,
                     global_max_time + timedelta(seconds=bin_size),
                     timedelta(seconds=bin_size)).astype(datetime)

    fig, axes = plt.subplots(nrows=2, ncols=3, sharex=True, sharey=False, figsize=(12, 8))
    # Layout: PLCs on left/middle, SCADA and Attacker on right
    # [0,0] PLC1    [0,1] PLC3    [0,2] SCADA
    # [1,0] PLC2    [1,1] PLC4    [1,2] Attacker

    # Color palette - distinct and professional
    colors = {
        "TCP-SYN": "#E63946",   # Vibrant red for attack traffic
        "TCP-DATA": "#2A9D8F", # Teal for normal data
        "ARP": "#457B9D",       # Steel blue for ARP
    }

    def plot_binned_times_detailed(ax, packet_times, title):
        bin_centers = [bin + timedelta(seconds=bin_size / 2) for bin in bins[:-1]]
        
        # Line styles for each packet type
        line_styles = {
            "TCP-SYN": {"color": "#E63946", "linestyle": "-", "linewidth": 2, "marker": "o", "markersize": 3},
            "TCP-DATA": {"color": "#2A9D8F", "linestyle": "-", "linewidth": 2, "marker": "s", "markersize": 3},
            "ARP": {"color": "#457B9D", "linestyle": "-", "linewidth": 2, "marker": "^", "markersize": 3},
        }
        
        labels_order = ["TCP-SYN", "TCP-DATA", "ARP"]
        
        for ptype in labels_order:
            if ptype in packet_times:
                binned_counts, _ = np.histogram(packet_times[ptype], bins=bins)
                if np.sum(binned_counts) > 0:
                    label_name = ptype.replace("TCP-", "TCP ")
                    style = line_styles[ptype]
                    ax.plot(bin_centers, binned_counts, label=label_name,
                           color=style["color"], linestyle=style["linestyle"], 
                           linewidth=style["linewidth"], marker=style["marker"],
                           markersize=style["markersize"], markevery=5)

        ax.set_title(title, fontsize=12, fontweight="bold", y=1.15)
        ax.set_ylabel("Packets", fontsize=10)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3, frameon=True, fancybox=True, framealpha=0.95, fontsize=8)
        ax.set_facecolor('white')
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', labelsize=9)
        ax.set_xlim(bin_centers[0], bin_centers[-1])


    # Plot in 2x3 grid: PLCs on left/middle, SCADA/Attacker on right
    plot_binned_times_detailed(axes[0, 0], packet_times_plc1, "PLC1")
    plot_binned_times_detailed(axes[1, 0], packet_times_plc2, "PLC2 (Attacked)")
    plot_binned_times_detailed(axes[0, 1], packet_times_plc4, "PLC4")
    plot_binned_times_detailed(axes[1, 1], packet_times_plc3, "PLC3 (Attacked)")
    plot_binned_times_detailed(axes[0, 2], packet_times_scada, "SCADA")
    plot_binned_times_detailed(axes[1, 2], packet_times_attacker, "Attacker")

    # Add x-axis labels to bottom row only
    axes[1, 0].set_xlabel("Time", fontsize=12, fontweight='bold')
    axes[1, 1].set_xlabel("Time", fontsize=12, fontweight='bold')
    axes[1, 2].set_xlabel("Time", fontsize=12, fontweight='bold')
    
    # Remove x-axis tick labels (keep just "Time" label)
    for ax in axes.flat:
        ax.set_xticklabels([])
    
    # Add subtle spines
    for ax in axes.flat:
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)
            spine.set_color('#CCCCCC')

    plt.subplots_adjust(top=0.85, hspace=0.5)
    plt.savefig('ScadaCaseNew/CyberLayer_PacketAnalysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved: ScadaCaseNew/CyberLayer_PacketAnalysis.png")

except ImportError:
    print("   ⚠ Skipped: scapy not installed (pip install scapy)")
except FileNotFoundError as e:
    print(f"   ⚠ Skipped: PCAP files not found - {e}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# ============================================
# 1. DoS WITHOUT Guard - Ground Truth
# ============================================
print("\n[1/4] Generating DoS No Guard - Ground Truth plot...")

try:
    ground_truth_df = pd.read_csv('../examples/EdenTown/Scada_Case/2_DoS_NoGuard/outputNew2/ground_truth.csv')
    scada_df = pd.read_csv('../examples/EdenTown/Scada_Case/2_DoS_NoGuard/outputNew2/scada_values.csv')
    ground_truth_df = ground_truth_df.drop(0)

    attack_intervals = find_attack_intervals(ground_truth_df, 'plc2AttackerUnit')
    attack_start, attack_end = attack_intervals[0]

    fig, axes = plt.subplots(3, 1, figsize=(6, 8), gridspec_kw={'height_ratios': [1, 1, 1]})

    # Tank Levels
    axes[0].plot(ground_truth_df['iteration'], ground_truth_df['T1_LEVEL'], label='T1', color='green', linewidth=2)
    axes[0].plot(ground_truth_df['iteration'], ground_truth_df['T2_LEVEL'], label='T2', color='green', linestyle='--', linewidth=2)
    axes[0].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack')
    axes[0].axvline(x=attack_end, color='red', linestyle='--', linewidth=2)
    axes[0].set_title("Tank Levels", fontsize=14, fontweight='bold', y=1.15)
    axes[0].set_ylabel("Level (m)", fontsize=12)
    axes[0].grid(True, alpha=0.3)
    adjust_ylim(axes[0], ['T1_LEVEL', 'T2_LEVEL'], ground_truth_df)
    add_legend_top_center(axes[0])

    # Pump Flows
    axes[1].plot(ground_truth_df['iteration'], ground_truth_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes[1].plot(ground_truth_df['iteration'], ground_truth_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes[1].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack')
    axes[1].axvline(x=attack_end, color='red', linestyle='--', linewidth=2)
    axes[1].set_title("Pump Flows", fontsize=14, fontweight='bold', y=1.15)
    axes[1].set_ylabel("Flow (CMH)", fontsize=12)
    axes[1].grid(True, alpha=0.3)
    adjust_ylim(axes[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_df)
    add_legend_top_center(axes[1])

    # Junction Pressures
    axes[2].plot(ground_truth_df['iteration'], ground_truth_df['J1_LEVEL'], label='J1', color='orange', linewidth=2)
    axes[2].plot(ground_truth_df['iteration'], ground_truth_df['J2_LEVEL'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes[2].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack')
    axes[2].axvline(x=attack_end, color='red', linestyle='--', linewidth=2)
    axes[2].set_title("Junction Pressures", fontsize=14, fontweight='bold', y=1.15)
    axes[2].set_ylabel("Pressure (m)", fontsize=12)
    axes[2].set_xlabel("Time (steps)", fontsize=12)
    axes[2].grid(True, alpha=0.3)
    adjust_ylim(axes[2], ['J1_LEVEL', 'J2_LEVEL'], ground_truth_df, min_override=50)
    add_legend_top_center(axes[2])

    plt.subplots_adjust(hspace=0.5)
    plt.savefig('ScadaCaseNew/DoS_NoGuard_GroundTruth.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved: ScadaCaseNew/DoS_NoGuard_GroundTruth.png")

except Exception as e:
    print(f"   ✗ Error: {e}")

# ============================================
# 2. DoS WITHOUT Guard - SCADA View
# ============================================
print("\n[2/4] Generating DoS No Guard - SCADA View plot...")

try:
    fig2, axes2 = plt.subplots(3, 1, figsize=(6, 8), sharex=True)

    # Tank Levels
    axes2[0].plot(scada_df['iteration'], scada_df['T1'], label='T1', color='green', linewidth=2)
    axes2[0].plot(scada_df['iteration'], scada_df['T2'], label='T2', color='green', linestyle='--', linewidth=2)
    axes2[0].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack')
    axes2[0].axvline(x=attack_end, color='red', linestyle='--', linewidth=2)
    axes2[0].set_title("Tank Levels", fontsize=14, fontweight='bold', y=1.15)
    axes2[0].set_ylabel("Level (m)", fontsize=12)
    axes2[0].grid(True, alpha=0.3)
    adjust_ylim(axes2[0], ['T1', 'T2'], scada_df)
    add_legend_top_center(axes2[0])

    # Pump Flows
    axes2[1].plot(ground_truth_df['iteration'], ground_truth_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes2[1].plot(ground_truth_df['iteration'], ground_truth_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes2[1].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack')
    axes2[1].axvline(x=attack_end, color='red', linestyle='--', linewidth=2)
    axes2[1].set_title("Pump Flows", fontsize=14, fontweight='bold', y=1.15)
    axes2[1].set_ylabel("Flow (CMH)", fontsize=12)
    axes2[1].grid(True, alpha=0.3)
    adjust_ylim(axes2[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_df)
    add_legend_top_center(axes2[1])

    # Junction Pressures
    axes2[2].plot(scada_df['iteration'], scada_df['J1'], label='J1', color='orange', linewidth=2)
    axes2[2].plot(scada_df['iteration'], scada_df['J2'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes2[2].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack')
    axes2[2].axvline(x=attack_end, color='red', linestyle='--', linewidth=2)
    axes2[2].set_title("Junction Pressures", fontsize=14, fontweight='bold', y=1.15)
    axes2[2].set_ylabel("Pressure (m)", fontsize=12)
    axes2[2].set_xlabel("Time (steps)", fontsize=12)
    axes2[2].grid(True, alpha=0.3)
    adjust_ylim(axes2[2], ['J1', 'J2'], scada_df, min_override=50)
    add_legend_top_center(axes2[2])

    plt.subplots_adjust(hspace=0.5)
    plt.savefig('ScadaCaseNew/DoS_NoGuard_ScadaView.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved: ScadaCaseNew/DoS_NoGuard_ScadaView.png")

except Exception as e:
    print(f"   ✗ Error: {e}")

# ============================================
# 3. DoS WITH Guard - Ground Truth
# ============================================
print("\n[3/4] Generating DoS WITH Guard - Ground Truth plot...")

try:
    ground_truth_guard_df = pd.read_csv('../examples/EdenTown/Scada_Case/3_DoS_WithGuard/outputNew3/ground_truth.csv')
    scada_guard_df = pd.read_csv('../examples/EdenTown/Scada_Case/3_DoS_WithGuard/outputNew3/scada_values.csv')
    ground_truth_guard_df = ground_truth_guard_df.drop(0)

    attack_intervals_guard = find_attack_intervals(ground_truth_guard_df, 'plc2AttackerUnit')
    attack_start_guard, attack_end_guard = attack_intervals_guard[0]

    fig3, axes3 = plt.subplots(3, 1, figsize=(6, 8), gridspec_kw={'height_ratios': [1, 1, 1]})

    # Tank Levels
    axes3[0].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['T1_LEVEL'], label='T1', color='green', linewidth=2)
    axes3[0].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['T2_LEVEL'], label='T2', color='green', linestyle='--', linewidth=2)
    axes3[0].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack')
    axes3[0].axvline(x=attack_end_guard, color='red', linestyle='--', linewidth=2)
    axes3[0].set_title("Tank Levels", fontsize=14, fontweight='bold', y=1.15)
    axes3[0].set_ylabel("Level (m)", fontsize=12)
    axes3[0].grid(True, alpha=0.3)
    adjust_ylim(axes3[0], ['T1_LEVEL', 'T2_LEVEL'], ground_truth_guard_df)
    add_legend_top_center(axes3[0])

    # Pump Flows
    axes3[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes3[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes3[1].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack')
    axes3[1].axvline(x=attack_end_guard, color='red', linestyle='--', linewidth=2)
    axes3[1].set_title("Pump Flows", fontsize=14, fontweight='bold', y=1.15)
    axes3[1].set_ylabel("Flow (CMH)", fontsize=12)
    axes3[1].grid(True, alpha=0.3)
    adjust_ylim(axes3[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_guard_df)
    add_legend_top_center(axes3[1])

    # Junction Pressures
    axes3[2].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['J1_LEVEL'], label='J1', color='orange', linewidth=2)
    axes3[2].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['J2_LEVEL'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes3[2].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack')
    axes3[2].axvline(x=attack_end_guard, color='red', linestyle='--', linewidth=2)
    axes3[2].set_title("Junction Pressures", fontsize=14, fontweight='bold', y=1.15)
    axes3[2].set_ylabel("Pressure (m)", fontsize=12)
    axes3[2].set_xlabel("Time (steps)", fontsize=12)
    axes3[2].grid(True, alpha=0.3)
    adjust_ylim(axes3[2], ['J1_LEVEL', 'J2_LEVEL'], ground_truth_guard_df, min_override=50)
    add_legend_top_center(axes3[2])

    plt.subplots_adjust(hspace=0.5)
    plt.savefig('ScadaCaseNew/DoS_WithGuard_GroundTruth.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved: ScadaCaseNew/DoS_WithGuard_GroundTruth.png")

except Exception as e:
    print(f"   ✗ Error: {e}")

# ============================================
# 4. DoS WITH Guard - SCADA View
# ============================================
print("\n[4/4] Generating DoS WITH Guard - SCADA View plot...")

try:
    fig4, axes4 = plt.subplots(3, 1, figsize=(6, 8), sharex=True)

    # Tank Levels
    axes4[0].plot(scada_guard_df['iteration'], scada_guard_df['T1'], label='T1', color='green', linewidth=2)
    axes4[0].plot(scada_guard_df['iteration'], scada_guard_df['T2'], label='T2', color='green', linestyle='--', linewidth=2)
    axes4[0].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack')
    axes4[0].axvline(x=attack_end_guard, color='red', linestyle='--', linewidth=2)
    axes4[0].set_title("Tank Levels", fontsize=14, fontweight='bold', y=1.15)
    axes4[0].set_ylabel("Level (m)", fontsize=12)
    axes4[0].grid(True, alpha=0.3)
    adjust_ylim(axes4[0], ['T1', 'T2'], scada_guard_df)
    add_legend_top_center(axes4[0])

    # Pump Flows
    axes4[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes4[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes4[1].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack')
    axes4[1].axvline(x=attack_end_guard, color='red', linestyle='--', linewidth=2)
    axes4[1].set_title("Pump Flows", fontsize=14, fontweight='bold', y=1.15)
    axes4[1].set_ylabel("Flow (CMH)", fontsize=12)
    axes4[1].grid(True, alpha=0.3)
    adjust_ylim(axes4[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_guard_df)
    add_legend_top_center(axes4[1])

    # Junction Pressures
    axes4[2].plot(scada_guard_df['iteration'], scada_guard_df['J1'], label='J1', color='orange', linewidth=2)
    axes4[2].plot(scada_guard_df['iteration'], scada_guard_df['J2'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes4[2].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack')
    axes4[2].axvline(x=attack_end_guard, color='red', linestyle='--', linewidth=2)
    axes4[2].set_title("Junction Pressures", fontsize=14, fontweight='bold', y=1.15)
    axes4[2].set_ylabel("Pressure (m)", fontsize=12)
    axes4[2].set_xlabel("Time (steps)", fontsize=12)
    axes4[2].grid(True, alpha=0.3)
    adjust_ylim(axes4[2], ['J1', 'J2'], scada_guard_df, min_override=50)
    add_legend_top_center(axes4[2])

    plt.subplots_adjust(hspace=0.5)
    plt.savefig('ScadaCaseNew/DoS_WithGuard_ScadaView.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved: ScadaCaseNew/DoS_WithGuard_ScadaView.png")

except Exception as e:
    print(f"   ✗ Error: {e}")

# ============================================
# Summary
# ============================================
print("\n" + "=" * 60)
print("Visualization Complete!")
print("=" * 60)
print("\nGenerated files in aaaMyViz/ScadaCaseNew/:")
print("  • CyberLayer_PacketAnalysis.png   - TCP/ARP packet traffic during attack")
print("  • DoS_NoGuard_GroundTruth.png     - Physical layer without guard")
print("  • DoS_NoGuard_ScadaView.png       - What SCADA sees (frozen data!)")
print("  • DoS_WithGuard_GroundTruth.png   - Physical layer WITH guard")
print("  • DoS_WithGuard_ScadaView.png     - SCADA view WITH guard")
print()

print()
