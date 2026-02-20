# Scanner Setup SOP

This SOP defines the current production-safe setup for barcode scanners and rack assignment operations.

## 1) Required Barcode Formats

- **Location barcode**: `LOC-...`
  - Example: `LOC-A1`, `LOC-RACK-12`
- **Order barcode (SKU)**: `ORD-########`
  - Example: `ORD-00000028`

If the scanned value does not match these formats, the app rejects it.

## 2) Scanner Device Configuration

Configure scanners in **HID keyboard mode** (acts like keyboard input):

1. Suffix: **Enter** (`CR` or `CRLF`)
2. Keep output uppercase if scanner supports it
3. Disable scanner-added prefixes/suffixes other than Enter

No custom driver is required in the current version.

## 3) Operator Flow (Rack Assignment)

1. Go to **Orders → Open Scan Station**
2. Scan location barcode (`LOC-...`)
3. If location is new, optionally enter rack number
4. Scan order barcode (`ORD-########`)
5. Confirm assignment

Shortcut behavior:
- If scanner reads a supported barcode while no text input is focused, app auto-opens the Orders scan station.

If location is occupied, app blocks assignment and prompts:
- rack already full
- option to clear rack and continue

## 4) Rack Status Checks

In Scan Station, use **Rack Status** panel:
- shows location barcode + rack number
- shows `Occupied` or `Empty`
- shows current assigned order SKU when occupied

Use **Refresh** after high-volume scanning or manual clear actions.

## 5) Pickup Flow

On pickup completion:
- app can prompt to clear the order’s rack assignment
- clearing removes location mapping from active order

## 6) Troubleshooting

- **Scanner does nothing**: verify HID mode and cursor focus in active scan field.
- **Barcode rejected**: verify prefix and format (`LOC-` / `ORD-########`).
- **Wrong order in rack**: use force-clear prompt only after physical verification.
- **Rack status stale**: click Refresh in Rack Status panel.

## 7) Current Limitations

- Browser print is used for tags (no background print daemon yet).
- HID keyboard mode only (no native scanner SDK integration).
- Rack capacity is one active order per location barcode.
