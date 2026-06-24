# Daily WSPR Path Matrix

Developed by John Loftus (VK4EMM) · Technical assistance: OpenAI

`index.html` is a self-contained browser application for studying WSPR spots received by one exact reporter callsign over a UTC day.

It produces two destination-area matrices in 30-minute UTC bins and nine WSPR bands:

- 160 m, 80 m, 40 m, 30 m, 20 m, 17 m, 15 m, 12 m, and 10 m.
- Path 1 and Path 2 are independently selected transmitter destination areas.
- Each destination area is defined by a city centre and selectable radius.

The application is intentionally a **single-reporter activity tool**. It does not determine propagation path type or predict contacts.

## What is counted

For a reporter such as `VK4EMM`, each matrix cell counts spots that meet all of these conditions:

1. The exact receiver/reporter callsign is `VK4EMM`.
2. The source row identifies that exact receiver callsign. The current application does not apply a receiver-grid or receiver-radius filter.
3. The spot timestamp belongs to the displayed 30-minute UTC bin.
4. The transmitting beacon grid is within the selected city radius for Path 1 or Path 2.
5. The spot is on the displayed band.

For example, `PATH 2 | Received by VK4EMM from North America — Denver area, 1,200 km radius` means beacons heard by `VK4EMM` whose transmitting grids are within 1,200 km of Denver.

The separate **All Beacons Heard by Reporter** matrix shows every beacon heard by the exact reporter callsign in the imported or collected data. It has no destination-area radius or beacon-continent filter.

## 30-minute bin convention

A row labelled `10:00` means:

```text
10:00:00 UTC <= spot time < 10:30:00 UTC
```

The ending time is exclusive. A spot at exactly `10:30:00` belongs in the `10:30` row, not the `10:00` row.

For normal WSPR-2 reports, this usually means timestamps from `10:00` through `10:28` UTC, because WSPR-2 transmissions are aligned to two-minute slots. The matrix rule remains the exact half-open interval above.

When comparing against another service, use the same exact half-hour UTC interval and the same receiver callsign.

## Use with saved WSPRnet data

1. Set Path 1 and Path 2 destination areas.
2. At WSPRnet, query one receiver/reporter callsign.
3. Leave **Unique** unchecked so the exported result retains individual timestamps.
4. Save one or more JSON, CSV, or HTML result files.
5. Select the files in **Import saved WSPRnet data**.
6. Confirm the detected reporter and date, then select **Build Matrix from WSPRnet Data**.

Overlapping source files are safe: exact duplicate rows are removed before counting.

## Use with wspr.live — manual collection

1. Enter the receiver callsign, for example `VK4EMM`.
2. Press a band button.
3. The application queries the latest fully completed 30-minute UTC bin, never a partial current bin.
4. Wait for the shared five-second cooldown before requesting another band.
5. Use **Build Matrix from wspr.live Data** at any time.

The same band becomes available again after the next completed bin. Rows are appended to the active UTC-day collection; completed bin-band pairs are not requested twice.

## Use with wspr.live — automatic full-day collection

Automatic full-day collection is explicitly started by the user with **Schedule Next Full UTC-Day**.

- A new full-day collection begins after `00:33 UTC`, when the first target bin (`00:00–00:30`) is complete and has a three-minute availability margin.
- The nine bands are requested one at a time, three minutes apart.
- In the trial build, each browser adds a random 20–120 second offset after that three-minute margin. Subsequent sets retain that same offset, so browsers do not all begin together.
- The band order rotates between bins, further reducing simultaneous requests for the same band across trial users.
- The final `23:30–00:00` bin is collected shortly after midnight, then automatic collection stops without starting a new UTC day.
- The active collection is stored in browser IndexedDB so its collected data survives a page reload. Automatic downloading does not resume after reload; starting it again is always a user action.

The status line reports the active UTC date, completed requests, collected bins, and any failed request. In the trial build, automatic collection retries a failed request once after a random 30–90 second delay. Three consecutive failed automatic requests pause collection for user review. A request that still fails remains recorded as missing rather than silently becoming a zero count.

Open **Request diagnostics** to see each unresolved request's band, UTC bin, attempt count, and returned error. The same information is retained in IndexedDB and in **Save Collected JSON**. Use **Retry Missing Requests** for an explicit, user-initiated retry of unresolved band-bins.

## Trial fairness mode

The trial build disables the seven-day continuous archive. This avoids unattended multi-day collection while operators are evaluating the application. Automatic collection remains user-started, staggered between browsers, constrained to one completed bin and one band per request, and stopped after the UTC day.

The browser tab must remain open for scheduled collection. Reloading restores the active collected data but does not silently resume automatic downloading.

## Current-day live collection

**Start Current-Day Live Collection** progressively acquires the current UTC day from the next staggered scheduled set. It begins with the preceding completed bin and continues with consecutive completed bins until the UTC date changes.

This mode is deliberately incomplete until the day ends. In a matrix built from collected live data:

- `—` means the band-bin is pending collection.
- `0` means that band-bin was collected and contained no matching spots.
- `!` means the band-bin request failed and requires later attention.

The status line reports the number of fully acquired bins out of 48. A current-day collection cannot backfill bins that were not collected before it was started; use saved WSPRnet data for historical coverage.

## Counting modes

Use the **Counting** buttons to cycle through:

- **Raw Spots** — every imported spot row.
- **Unique Beacons Per Bin** — each beacon callsign once per 30-minute bin, band, and destination area.
- **Cumulative Unique Beacons** — a running unique-beacon total across the UTC day.

Raw Spots is the appropriate mode when comparing unaggregated source spot records.

## Save, export, and print

- **Save Collected JSON** downloads the currently collected wspr.live source rows and request history.
- **Export CSV** downloads the completed matrix and its metadata.
- **Print / PDF** opens the browser print workflow for a matrix report.

The collected JSON is the audit record for checking a result against another WSPR service.

## Data-source and interpretation notes

- wspr.live requests use UTC query bounds and UTC timestamps.
- The wspr.live collector fetches only one exact receiver callsign, one band, and one completed 30-minute bin per request.
- A missing cell is not proof that propagation was impossible; it means no matching source row was counted for that cell and data set.
- A destination radius is applied to the transmitter grid, not to the reporter. The reporter is selected by exact callsign.
- Do not compare a single-reporter matrix count with an area-to-area activity report unless their receiver filter, transmitter-area definition, raw/unique mode, and UTC interval are identical.

## Files

- `index.html` — Daily WSPR Path Matrix application.
- `long-path_index.html` — preserved snapshot of the earlier long-path application.
