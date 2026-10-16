# SPDX-License-Identifier: GPL-2.0-or-later
import json
from pathlib import Path
import sys
from measure import compare

root=Path(sys.argv[1])
for mode in ['normal','studio']:
    reports=[]
    for flavor in ['upstream','vision']:
        matches=list((root/f'parity-{flavor}').glob(f'**/{mode}/measurements.json'))
        assert len(matches)==1,(flavor,mode,matches)
        reports.append(json.loads(matches[0].read_text()))
    compare(*reports)
    print(f'PASS: {mode}: recorded audio, scenes, image/browser CSS and fade match within stated tolerances.')
print('Physical cameras, speech recognition and external streaming destinations are not covered by this test.')
