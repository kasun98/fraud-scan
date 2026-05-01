import http   from 'k6/http'
import { check, sleep } from 'k6'
import { Trend, Counter, Rate } from 'k6/metrics'

const scoringLatency = new Trend('scoring_latency_ms', true)
const totalSent      = new Counter('transactions_sent')
const errorRate      = new Rate('error_rate')

export const options = {
  stages: [
    { duration: '30s', target: 10  },   // warm up
    { duration: '1m',  target: 50  },   // normal load
    { duration: '1m',  target: 100 },   // high load — should trigger HPA
    { duration: '30s', target: 200 },   // peak
    { duration: '1m',  target: 50  },   // scale down
    { duration: '30s', target: 0   },   // done
  ],
  thresholds: {
    'scoring_latency_ms': ['p(95) < 200'],
    'error_rate':         ['rate < 0.05'],
  },
}

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8001'

const CATEGORIES = ['ecommerce','grocery','streaming','fuel',
                    'transport','electronics','digital_goods','travel']
const METHODS    = ['credit_card','debit_card','digital_wallet']
const CHANNELS   = ['web','mobile','pos']

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function makeTransaction(fraud = false) {
  const userId = `user-${String(Math.floor(Math.random() * 500)).padStart(4,'0')}`
  if (fraud) {
    return {
      transaction_id:       `k6-fraud-${__VU}-${__ITER}`,
      user_id:              userId,
      amount:               Math.random() * 50000 + 10000,
      currency:             'USD',
      merchant_name:        'Fast Cash Transfer',
      merchant_category:    'money_transfer',
      merchant_country:     'RU',
      user_country:         'US',
      payment_method:       'bank_transfer',
      channel:              'api',
      txn_count_user:       Math.floor(Math.random() * 5),
      hours_since_last_txn: Math.random() * 2,
      amount_deviation:     Math.random() * 15 + 5,
      geo_distance_km:      Math.random() * 8000 + 4000,
      is_new_device:        1,
      is_high_risk_country: 1,
      is_cross_border:      1,
      velocity_10min:       Math.floor(Math.random() * 8) + 3,
    }
  }
  return {
    transaction_id:       `k6-${__VU}-${__ITER}-${Date.now()}`,
    user_id:              userId,
    amount:               Math.random() * 500 + 10,
    currency:             'USD',
    merchant_name:        'Amazon',
    merchant_category:    randomItem(CATEGORIES),
    merchant_country:     'US',
    user_country:         'US',
    payment_method:       randomItem(METHODS),
    channel:              randomItem(CHANNELS),
    txn_count_user:       Math.floor(Math.random() * 100),
    hours_since_last_txn: Math.random() * 48,
    amount_deviation:     Math.random() * 2,
    geo_distance_km:      Math.random() * 50,
    is_new_device:        0,
    is_high_risk_country: 0,
    is_cross_border:      0,
    velocity_10min:       Math.floor(Math.random() * 3),
  }
}

export default function () {
  const isFraud = Math.random() < 0.02
  const payload = JSON.stringify(makeTransaction(isFraud))
  const start   = Date.now()

  const res = http.post(
    `${BASE_URL}/api/v1/score`,
    payload,
    { headers: { 'Content-Type': 'application/json' }, timeout: '10s' },
  )

  const latency = Date.now() - start
  scoringLatency.add(latency)
  totalSent.add(1)

  const ok = check(res, {
    'status 200':      r => r.status === 200,
    'has decision':    r => {
      try { return JSON.parse(r.body).decision !== undefined }
      catch { return false }
    },
  })

  errorRate.add(!ok)
  sleep(0.05)
}

export function handleSummary(data) {
  const p50  = data.metrics.scoring_latency_ms?.values?.['p(50)']?.toFixed(1)  || 'N/A'
  const p95  = data.metrics.scoring_latency_ms?.values?.['p(95)']?.toFixed(1)  || 'N/A'
  const p99  = data.metrics.scoring_latency_ms?.values?.['p(99)']?.toFixed(1)  || 'N/A'
  const sent = data.metrics.transactions_sent?.values?.count                    || 0
  const errs = ((data.metrics.error_rate?.values?.rate || 0) * 100).toFixed(2)

  return {
    stdout: `
╔══════════════════════════════════════════╗
║       Fraud Detection Load Test          ║
╠══════════════════════════════════════════╣
║  Transactions sent : ${String(sent).padEnd(20)}║
║  Error rate        : ${(errs + '%').padEnd(20)}║
║  Latency P50       : ${(p50 + 'ms').padEnd(20)}║
║  Latency P95       : ${(p95 + 'ms').padEnd(20)}║
║  Latency P99       : ${(p99 + 'ms').padEnd(20)}║
╚══════════════════════════════════════════╝
`,
  }
}