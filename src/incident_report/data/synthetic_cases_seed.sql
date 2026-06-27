PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS status_events;
DROP TABLE IF EXISTS synthetic_cases;

CREATE TABLE synthetic_cases (
    case_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    prompt TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    contract_tier TEXT NOT NULL CHECK (contract_tier IN ('free', 'pro', 'enterprise')),
    customer_region TEXT NOT NULL,
    expected_service TEXT NOT NULL,
    expected_status TEXT NOT NULL CHECK (expected_status IN ('operational', 'degraded', 'outage')),
    expected_email_action TEXT NOT NULL CHECK (
        expected_email_action IN ('email sent', 'email skipped', 'email not needed')
    )
);

CREATE TABLE status_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES synthetic_cases(case_id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    service TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('operational', 'degraded', 'outage')),
    region TEXT NOT NULL,
    minutes_ago INTEGER NOT NULL CHECK (minutes_ago >= 0),
    note TEXT NOT NULL
);

CREATE INDEX idx_status_events_case_id_sort ON status_events(case_id, sort_order);

INSERT INTO synthetic_cases (
    case_id,
    description,
    prompt,
    customer_name,
    contract_tier,
    customer_region,
    expected_service,
    expected_status,
    expected_email_action
) VALUES
(
    'search-outage',
    'Customer reports search timeouts during a known regional outage.',
    'Northstar Clinic says search is timing out. Check the search status and summarize what to do next.',
    'Northstar Clinic',
    'enterprise',
    'us-east',
    'search',
    'outage',
    'email sent'
),
(
    'api-degraded',
    'API latency is elevated but the service is still partially available.',
    'Cobalt Retail reports slow checkout API calls in us-west. Check API health and tell support what should happen next.',
    'Cobalt Retail',
    'pro',
    'us-west',
    'api',
    'degraded',
    'email sent'
),
(
    'auth-operational',
    'Customer login complaint with healthy auth telemetry.',
    'Helio Labs says one user cannot sign in. Check auth status and decide whether this looks like a platform incident.',
    'Helio Labs',
    'free',
    'global',
    'auth',
    'operational',
    'email not needed'
),
(
    'billing-false-alarm',
    'Payment concern after a customer-side card decline, not an incident.',
    'Summit Fitness says a payment failed for one member. Check billing status and summarize whether engineering needs to respond.',
    'Summit Fitness',
    'pro',
    'us-east',
    'billing',
    'operational',
    'email not needed'
),
(
    'multi-service-regional',
    'Regional storage issue causes API degradation with related search noise.',
    'Evergreen Bank reports dashboard API timeouts in eu-central. Check API health and summarize whether there is an active incident.',
    'Evergreen Bank',
    'enterprise',
    'eu-central',
    'api',
    'degraded',
    'email sent'
),
(
    'unknown-service',
    'Prompt references an unsupported service name absent from status data.',
    'Atlas School says exports are stuck. Check export status and tell the support team what to do next if there is no matching status event.',
    'Atlas School',
    'pro',
    'us-east',
    'exports',
    'operational',
    'email not needed'
);

INSERT INTO status_events (
    case_id,
    sort_order,
    service,
    state,
    region,
    minutes_ago,
    note
) VALUES
('search-outage', 1, 'api', 'degraded', 'us-east', 35, 'p95 latency above 8 seconds after queue depth spike'),
('search-outage', 2, 'auth', 'operational', 'global', 10, 'login and token refresh success rate within normal range'),
('search-outage', 3, 'search', 'outage', 'us-east', 42, 'index workers throttled by upstream storage errors'),

('api-degraded', 1, 'api', 'degraded', 'us-west', 18, 'checkout requests delayed by database connection pool saturation'),
('api-degraded', 2, 'billing', 'operational', 'us-west', 8, 'invoice creation and payment capture within baseline'),
('api-degraded', 3, 'search', 'operational', 'us-west', 6, 'query latency and indexing backlog within normal range'),

('auth-operational', 1, 'auth', 'operational', 'global', 4, 'login success rate 99.98 percent and token refresh latency normal'),
('auth-operational', 2, 'api', 'operational', 'global', 7, 'request volume and error rate within expected range'),
('auth-operational', 3, 'billing', 'operational', 'global', 12, 'payment provider callbacks processing normally'),

('billing-false-alarm', 1, 'billing', 'operational', 'us-east', 5, 'card declines are isolated and gateway availability is normal'),
('billing-false-alarm', 2, 'auth', 'operational', 'global', 6, 'admin and member login success rate stable'),
('billing-false-alarm', 3, 'api', 'operational', 'us-east', 10, 'no elevated 5xx or timeout rate detected'),

('multi-service-regional', 1, 'api', 'degraded', 'eu-central', 26, 'dashboard API p95 latency elevated after regional storage failover'),
('multi-service-regional', 2, 'search', 'degraded', 'eu-central', 24, 'index freshness delayed while storage failover catches up'),
('multi-service-regional', 3, 'auth', 'operational', 'global', 9, 'identity provider checks passing'),

('unknown-service', 1, 'api', 'operational', 'us-east', 6, 'request success rate and latency within normal range'),
('unknown-service', 2, 'billing', 'operational', 'us-east', 11, 'subscription and invoice jobs are current'),
('unknown-service', 3, 'search', 'operational', 'us-east', 14, 'queries and indexing are healthy');
