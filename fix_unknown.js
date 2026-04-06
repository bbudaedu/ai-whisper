const fs = require('fs');
const path = require('path');

const p01 = path.join('.planning/phases/02-api', '02-01-PLAN.md');
let c01 = fs.readFileSync(p01, 'utf8');
c01 = c01.replace(/<files>UNKNOWN_PLEASE_FIX<\/files>/g, '<files>pipeline/queue/models.py, tests/test_external_api_auth.py, tests/test_external_api_tasks.py, tests/test_external_api_download.py</files>');
fs.writeFileSync(p01, c01);
