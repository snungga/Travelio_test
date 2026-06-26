// C2 — MongoDB
// Count of messages per intent, per day, for the last 7 days, sorted by day.
//
// Collection: messages({ _id, guest_id, text, intent, created_at })
//
// Notes / assumptions:
//  * "Last 7 days" = created_at >= now - 7 days. We compute the bound in the
//    pipeline with $$NOW so it needs no app-side date wiring.
//  * Days are bucketed in UTC via $dateTrunc. Pass a `timezone` to $dateTrunc
//    (e.g. "Asia/Jakarta") if reports should follow local calendar days.
//  * Sorted by day ascending, then intent for stable, readable output.

db.messages.aggregate([
  {
    $match: {
      created_at: {
        $gte: new Date(new Date().getTime() - 7 * 24 * 60 * 60 * 1000)
      }
    }
  },
  {
    $group: {
      _id: {
        day: { $dateTrunc: { date: "$created_at", unit: "day" } },
        intent: "$intent"
      },
      count: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      day: "$_id.day",
      intent: "$_id.intent",
      count: 1
    }
  },
  { $sort: { day: 1, intent: 1 } }
]);
