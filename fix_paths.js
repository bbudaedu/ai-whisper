const fs = require('fs');
const path = require('path');

const file02 = path.join('.planning/phases/02-api', '02-02-PLAN.md');
let content = fs.readFileSync(file02, 'utf8');

// Fix the file path issue caused by the regex
content = content.replace(/api\/schemas\.py \(D-05: minimum token claims, D-02: short-lived \+ refresh\)/g, 'api/schemas.py');

// Add the references clearly in the action instead
content = content.replace(/1. Create `api\/schemas\.py`\. Add Pydantic models:/,
  '1. Create `api/schemas.py`. Add Pydantic models (respecting D-05 minimum claims and D-02 short-lived+refresh):');

content = content.replace(/create_access_token, create_refresh_token/, 'create_access_token');
content = content.replace(/create_access_token, create_refresh_token/g, 'create_access_token` and `create_refresh_token');

// Also fix grep validation
content = content.replace(/grep -q "create_access_token" and "create_refresh_token" api\/auth\.py/, 'grep -q "create_access_token" api/auth.py && grep -q "create_refresh_token" api/auth.py');
content = content.replace(/grep -q "create_access_token` and `create_refresh_token"/, 'grep -q "create_access_token"');

fs.writeFileSync(file02, content);

const file03 = path.join('.planning/phases/02-api', '02-03-PLAN.md');
content = fs.readFileSync(file03, 'utf8');
content = content.replace(/@router.post\("\/"\) \(D-08\)/, '@router.post("/")');
fs.writeFileSync(file03, content);
