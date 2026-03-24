const fs = require('fs');
const path = require('path');

const plans = [
  '02-01-PLAN.md',
  '02-02-PLAN.md',
  '02-03-PLAN.md',
  '02-04-PLAN.md',
  '02-05-PLAN.md'
];

plans.forEach(planFile => {
  const filePath = path.join('.planning/phases/02-api', planFile);
  if (!fs.existsSync(filePath)) return;

  let content = fs.readFileSync(filePath, 'utf8');

  // Ensure truths are strictly user-perspective and outcome-shaped
  if (planFile === '02-01-PLAN.md') {
    content = content.replace(/truths:[\s\S]*?artifacts:/, `truths:
    - "System tracks who created which task."
    - "Tasks can be tracked in queued and canceled states."
  artifacts:`);
  }

  // Double check that API-09 through 25 are referenced
  if (planFile === '02-03-PLAN.md') {
      content = content.replace(/Ensure D-11.*?covered\./, 'Ensure D-11 (multipart for upload), D-12 (youtube url), D-14 (multi-format output support) are covered. Also D-09 (minimum fields).');
  }

  fs.writeFileSync(filePath, content);
});