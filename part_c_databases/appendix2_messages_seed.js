// Appendix 2 — Sample data (MongoDB)
// The `messages` example doc is from the assessment PDF; the inserts below are a
// small seed so the C2 aggregation can be run and eyeballed.
//
// Run order: this file first (in mongosh), then c2_mongo_messages_per_intent_per_day.js.
// (A runnable, no-install version lives in demo/run_c2_mongomock.py.)
//
// created_at values are written relative to "now" so they land inside the
// last-7-days window the C2 query looks at.

const now = new Date();
const daysAgo = (n) => new Date(now.getTime() - n * 24 * 60 * 60 * 1000);

db.messages.insertMany([
  // ---- within the last 7 days (counted) ----
  { guest_id: 8821, text: "AC bocor, tolong kirim teknisi", intent: "maintenance_request", created_at: daysAgo(0) },
  { guest_id: 8822, text: "mau booking 2br di Kemang",       intent: "booking_inquiry",     created_at: daysAgo(0) },
  { guest_id: 8823, text: "bisa extend sampai senin?",        intent: "extension_request",   created_at: daysAgo(1) },
  { guest_id: 8824, text: "mau booking studio",               intent: "booking_inquiry",     created_at: daysAgo(1) },
  { guest_id: 8825, text: "wastafel mampet",                  intent: "maintenance_request", created_at: daysAgo(1) },
  { guest_id: 8826, text: "bayar dimana ya",                  intent: "payment_question",    created_at: daysAgo(3) },
  { guest_id: 8827, text: "ada unit kosong akhir bulan?",     intent: "booking_inquiry",     created_at: daysAgo(6) },
  // ---- older than 7 days (excluded by the date filter) ----
  { guest_id: 8828, text: "pesan lama",                       intent: "booking_inquiry",     created_at: daysAgo(10) },
]);
