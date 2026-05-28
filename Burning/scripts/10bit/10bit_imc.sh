toggled_value=$(printf %X $((16#`setpci -s:00:01.0 0x98.w` | 16#`printf '%X\n' "$((1 << 12))"`)));
setpci -s:00:01.0 0x98.w=$toggled_value;
toggled_value=$(printf %X $((16#`setpci -s:00:01.6 0x98.w` | 16#`printf '%X\n' "$((1 << 12))"`)));
setpci -s:00:01.6 0x98.w=$toggled_value;
toggled_value=$(printf %X $((16#`setpci -s:00:01.7 0x98.w` | 16#`printf '%X\n' "$((1 << 12))"`)));
setpci -s:00:01.7 0x98.w=$toggled_value;
