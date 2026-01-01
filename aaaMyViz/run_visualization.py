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
    """Add legend at top center, inside the plot area but above data."""
    ax.legend(loc='upper center', ncol=4, frameon=True, fancybox=True, 
              framealpha=0.9, fontsize=9)

# ============================================
# 0. Cyber Layer - Packet Analysis (PCAP)
# ============================================
print("\n[0/4] Generating Cyber Layer - Packet Analysis plot...")

try:
    from scapy.all import rdpcap
    import seaborn as sns
    sns.set_theme(style="whitegrid")
    
    def classify_packet(packet):
        """Classify packet type."""
        if packet.haslayer("ARP"):
            return "ARP"
        elif packet.haslayer("ICMP"):
            return "ICMP"
        elif packet.haslayer("TCP"):
            return "TCP"
        elif packet.haslayer("UDP"):
            return "UDP"
        else:
            return "Other"

    def process_pcap_by_time(file_path):
        """Process pcap file and extract timestamps by packet type."""
        packets = rdpcap(file_path)
        packet_times = {}

        for packet in packets:
            packet_type = classify_packet(packet)
            packet_time = datetime.fromtimestamp(float(packet.time))

            if packet_type not in packet_times:
                packet_times[packet_type] = []

            packet_times[packet_type].append(packet_time)

        return packet_times

    # Load pcap files from DoS No Guard scenario
    file_path1 = '../examples/EdenTown/Scada_Case/3_DoS_WithGuard/outputNew3/PLC3-eth0.pcap'
    file_path2 = '../examples/EdenTown/Scada_Case/3_DoS_WithGuard/outputNew3/plc3Attac-eth0.pcap'
    file_path3 = '../examples/EdenTown/Scada_Case/3_DoS_WithGuard/outputNew3/scada-eth0.pcap'

    packet_times1 = process_pcap_by_time(file_path1)
    packet_times2 = process_pcap_by_time(file_path2)
    packet_times3 = process_pcap_by_time(file_path3)

    # Gather all timestamps to determine global min and max
    all_times = []
    for pt_dict in [packet_times1, packet_times2, packet_times3]:
        for times in pt_dict.values():
            all_times.extend(times)

    bin_size = 5  # seconds
    global_min_time = min(all_times)
    global_max_time = max(all_times)

    # Create global bins
    bins = np.arange(global_min_time,
                     global_max_time + timedelta(seconds=bin_size),
                     timedelta(seconds=bin_size)).astype(datetime)

    fig, axes = plt.subplots(nrows=3, ncols=1, sharex=True, figsize=(10, 8))
    titles = ("Targeted PLC (PLC3)", "Malicious Attacker Component", "SCADA")

    def plot_binned_times(ax, packet_times, title):
        for packet_type, times in packet_times.items():
            binned_counts, _ = np.histogram(times, bins=bins)
            bin_centers = [bin + timedelta(seconds=bin_size / 2) for bin in bins[:-1]]

            if packet_type == "ARP":
                ax.plot(bin_centers, binned_counts, label=packet_type, linestyle='-', linewidth=2, color='#1E5AA8')
            if packet_type == "TCP":
                ax.plot(bin_centers, binned_counts, label=packet_type, linestyle='-', linewidth=3, color='#D95F02')

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_ylabel("Packet Count")
        ax.legend(loc='upper center', ncol=2, frameon=True, fancybox=True, framealpha=0.9, fontsize=9)
        ax.grid(True, alpha=0.3)

    plot_binned_times(axes[0], packet_times1, titles[0])
    plot_binned_times(axes[1], packet_times2, titles[1])
    plot_binned_times(axes[2], packet_times3, titles[2])

    axes[2].set_xlabel("Time")
    axes[0].set_xticks([])

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig('ScadaCaseNew/CyberLayer_PacketAnalysis.png', dpi=150, bbox_inches='tight')
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

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [1, 1, 1]})

    # Tank Levels
    axes[0].plot(ground_truth_df['iteration'], ground_truth_df['T1_LEVEL'], label='T1', color='green', linewidth=2)
    axes[0].plot(ground_truth_df['iteration'], ground_truth_df['T2_LEVEL'], label='T2', color='green', linestyle='--', linewidth=2)
    axes[0].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes[0].axvline(x=attack_end, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes[0].set_title("Tank Levels", fontsize=12, fontweight='bold')
    axes[0].set_ylabel("Level (m)")
    axes[0].grid(True, alpha=0.3)
    adjust_ylim(axes[0], ['T1_LEVEL', 'T2_LEVEL'], ground_truth_df)
    add_legend_top_center(axes[0])

    # Pump Flows
    axes[1].plot(ground_truth_df['iteration'], ground_truth_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes[1].plot(ground_truth_df['iteration'], ground_truth_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes[1].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes[1].axvline(x=attack_end, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes[1].set_title("Pump Flows", fontsize=12, fontweight='bold')
    axes[1].set_ylabel("Flow (CMH)")
    axes[1].grid(True, alpha=0.3)
    adjust_ylim(axes[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_df)
    add_legend_top_center(axes[1])

    # Junction Pressures
    axes[2].plot(ground_truth_df['iteration'], ground_truth_df['J1_LEVEL'], label='J1', color='orange', linewidth=2)
    axes[2].plot(ground_truth_df['iteration'], ground_truth_df['J2_LEVEL'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes[2].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes[2].axvline(x=attack_end, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes[2].set_title("Junction Pressures", fontsize=12, fontweight='bold')
    axes[2].set_ylabel("Pressure (m)")
    axes[2].set_xlabel("Time (steps)")
    axes[2].grid(True, alpha=0.3)
    adjust_ylim(axes[2], ['J1_LEVEL', 'J2_LEVEL'], ground_truth_df, min_override=50)
    add_legend_top_center(axes[2])

    plt.tight_layout()
    plt.savefig('ScadaCaseNew/DoS_NoGuard_GroundTruth.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved: ScadaCaseNew/DoS_NoGuard_GroundTruth.png")

except Exception as e:
    print(f"   ✗ Error: {e}")

# ============================================
# 2. DoS WITHOUT Guard - SCADA View
# ============================================
print("\n[2/4] Generating DoS No Guard - SCADA View plot...")

try:
    fig2, axes2 = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    # Tank Levels
    axes2[0].plot(scada_df['iteration'], scada_df['T1'], label='T1', color='green', linewidth=2)
    axes2[0].plot(scada_df['iteration'], scada_df['T2'], label='T2', color='green', linestyle='--', linewidth=2)
    axes2[0].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes2[0].axvline(x=attack_end, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes2[0].set_title("Tank Levels", fontsize=12, fontweight='bold')
    axes2[0].set_ylabel("Level (m)")
    axes2[0].grid(True, alpha=0.3)
    adjust_ylim(axes2[0], ['T1', 'T2'], scada_df)
    add_legend_top_center(axes2[0])

    # Pump Flows
    axes2[1].plot(ground_truth_df['iteration'], ground_truth_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes2[1].plot(ground_truth_df['iteration'], ground_truth_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes2[1].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes2[1].axvline(x=attack_end, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes2[1].set_title("Pump Flows", fontsize=12, fontweight='bold')
    axes2[1].set_ylabel("Flow (CMH)")
    axes2[1].grid(True, alpha=0.3)
    adjust_ylim(axes2[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_df)
    add_legend_top_center(axes2[1])

    # Junction Pressures
    axes2[2].plot(scada_df['iteration'], scada_df['J1'], label='J1', color='orange', linewidth=2)
    axes2[2].plot(scada_df['iteration'], scada_df['J2'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes2[2].axvline(x=attack_start, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes2[2].axvline(x=attack_end, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes2[2].set_title("Junction Pressures", fontsize=12, fontweight='bold')
    axes2[2].set_ylabel("Pressure (m)")
    axes2[2].set_xlabel("Time (steps)")
    axes2[2].grid(True, alpha=0.3)
    adjust_ylim(axes2[2], ['J1', 'J2'], scada_df, min_override=50)
    add_legend_top_center(axes2[2])

    plt.tight_layout()
    plt.savefig('ScadaCaseNew/DoS_NoGuard_ScadaView.png', dpi=150, bbox_inches='tight')
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

    fig3, axes3 = plt.subplots(3, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [1, 1, 1]})

    # Tank Levels
    axes3[0].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['T1_LEVEL'], label='T1', color='green', linewidth=2)
    axes3[0].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['T2_LEVEL'], label='T2', color='green', linestyle='--', linewidth=2)
    axes3[0].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes3[0].axvline(x=attack_end_guard, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes3[0].set_title("Tank Levels", fontsize=12, fontweight='bold')
    axes3[0].set_ylabel("Level (m)")
    axes3[0].grid(True, alpha=0.3)
    adjust_ylim(axes3[0], ['T1_LEVEL', 'T2_LEVEL'], ground_truth_guard_df)
    add_legend_top_center(axes3[0])

    # Pump Flows
    axes3[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes3[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes3[1].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes3[1].axvline(x=attack_end_guard, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes3[1].set_title("Pump Flows", fontsize=12, fontweight='bold')
    axes3[1].set_ylabel("Flow (CMH)")
    axes3[1].grid(True, alpha=0.3)
    adjust_ylim(axes3[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_guard_df)
    add_legend_top_center(axes3[1])

    # Junction Pressures
    axes3[2].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['J1_LEVEL'], label='J1', color='orange', linewidth=2)
    axes3[2].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['J2_LEVEL'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes3[2].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes3[2].axvline(x=attack_end_guard, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes3[2].set_title("Junction Pressures", fontsize=12, fontweight='bold')
    axes3[2].set_ylabel("Pressure (m)")
    axes3[2].set_xlabel("Time (steps)")
    axes3[2].grid(True, alpha=0.3)
    adjust_ylim(axes3[2], ['J1_LEVEL', 'J2_LEVEL'], ground_truth_guard_df, min_override=50)
    add_legend_top_center(axes3[2])

    plt.tight_layout()
    plt.savefig('ScadaCaseNew/DoS_WithGuard_GroundTruth.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("   ✓ Saved: ScadaCaseNew/DoS_WithGuard_GroundTruth.png")

except Exception as e:
    print(f"   ✗ Error: {e}")

# ============================================
# 4. DoS WITH Guard - SCADA View
# ============================================
print("\n[4/4] Generating DoS WITH Guard - SCADA View plot...")

try:
    fig4, axes4 = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    # Tank Levels
    axes4[0].plot(scada_guard_df['iteration'], scada_guard_df['T1'], label='T1', color='green', linewidth=2)
    axes4[0].plot(scada_guard_df['iteration'], scada_guard_df['T2'], label='T2', color='green', linestyle='--', linewidth=2)
    axes4[0].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes4[0].axvline(x=attack_end_guard, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes4[0].set_title("Tank Levels", fontsize=12, fontweight='bold')
    axes4[0].set_ylabel("Level (m)")
    axes4[0].grid(True, alpha=0.3)
    adjust_ylim(axes4[0], ['T1', 'T2'], scada_guard_df)
    add_legend_top_center(axes4[0])

    # Pump Flows
    axes4[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P1_FLOW'], label='P1', color='purple', linewidth=2)
    axes4[1].plot(ground_truth_guard_df['iteration'], ground_truth_guard_df['P2_FLOW'], label='P2', color='magenta', linewidth=2)
    axes4[1].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes4[1].axvline(x=attack_end_guard, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes4[1].set_title("Pump Flows", fontsize=12, fontweight='bold')
    axes4[1].set_ylabel("Flow (CMH)")
    axes4[1].grid(True, alpha=0.3)
    adjust_ylim(axes4[1], ['P1_FLOW', 'P2_FLOW'], ground_truth_guard_df)
    add_legend_top_center(axes4[1])

    # Junction Pressures
    axes4[2].plot(scada_guard_df['iteration'], scada_guard_df['J1'], label='J1', color='orange', linewidth=2)
    axes4[2].plot(scada_guard_df['iteration'], scada_guard_df['J2'], label='J2', color='darkorange', linestyle='--', linewidth=2)
    axes4[2].axvline(x=attack_start_guard, color='red', linestyle='--', linewidth=2, label='Attack Start')
    axes4[2].axvline(x=attack_end_guard, color='red', linestyle=':', linewidth=2, label='Attack End')
    axes4[2].set_title("Junction Pressures", fontsize=12, fontweight='bold')
    axes4[2].set_ylabel("Pressure (m)")
    axes4[2].set_xlabel("Time (steps)")
    axes4[2].grid(True, alpha=0.3)
    adjust_ylim(axes4[2], ['J1', 'J2'], scada_guard_df, min_override=50)
    add_legend_top_center(axes4[2])

    plt.tight_layout()
    plt.savefig('ScadaCaseNew/DoS_WithGuard_ScadaView.png', dpi=150, bbox_inches='tight')
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
