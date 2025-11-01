mkdir -p crm/cron_jobs
cat > crm/cron_jobs/clean_inactive_customers.sh <<'BASH'

#!/bin/bash
set -euo pipefail


LOG_FILE="/tmp/customer_cleanup_log.txt"

# Resolve project root (two levels up from crm/cron_jobs/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Allow overriding the Python binary (for venvs), default to python3
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Timestamp for log
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

# Run from project root so manage.py is in CWD
cd "$PROJECT_ROOT"

# Delete customers with NO orders since 1 year ago (includes customers with no orders at all)
# Prints the number of deleted customers; we capture that and append to a log.
DELETED_COUNT="$($PYTHON_BIN manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from crm.models import Customer

cutoff = timezone.now() - timedelta(days=365)
qs = Customer.objects.filter(~Q(orders__order_date__gte=cutoff)).distinct()
count = qs.count()
qs.delete()
print(count)
" 2>/dev/null | tail -n 1)"

echo "[$TIMESTAMP] Deleted customers: ${DELETED_COUNT:-0}" >> \"$LOG_FILE\"
BASH

chmod +x crm/cron_jobs/clean_inactive_customers.sh
