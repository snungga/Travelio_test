"""Runnable demo for C2 — messages per intent, per day, last 7 days.

Uses `mongomock` (pure-Python, in-memory Mongo) so no server is needed.

Dialect note: the canonical answer in
`c2_mongo_messages_per_intent_per_day.js` buckets days with `$dateTrunc`, which is
the idiomatic operator on a real MongoDB server. mongomock doesn't implement
`$dateTrunc`, so this demo uses the equivalent `$dateToString` (format
"%Y-%m-%d") to bucket by UTC day. The pipeline shape ($match -> $group -> $sort)
is otherwise identical.

Run:  python part_c_databases/demo/run_c2_mongomock.py   (needs `pip install mongomock`)
"""

from __future__ import annotations

import datetime as dt

import mongomock

NOW = dt.datetime(2026, 6, 27, 12, 0, 0)  # fixed "now" for deterministic output


def days_ago(n: int) -> dt.datetime:
    return NOW - dt.timedelta(days=n)


def seed(collection) -> None:
    collection.insert_many(
        [
            # within last 7 days (counted)
            {"guest_id": 8821, "intent": "maintenance_request", "created_at": days_ago(0)},
            {"guest_id": 8822, "intent": "booking_inquiry", "created_at": days_ago(0)},
            {"guest_id": 8823, "intent": "extension_request", "created_at": days_ago(1)},
            {"guest_id": 8824, "intent": "booking_inquiry", "created_at": days_ago(1)},
            {"guest_id": 8825, "intent": "maintenance_request", "created_at": days_ago(1)},
            {"guest_id": 8826, "intent": "payment_question", "created_at": days_ago(3)},
            {"guest_id": 8827, "intent": "booking_inquiry", "created_at": days_ago(6)},
            # older than 7 days (excluded)
            {"guest_id": 8828, "intent": "booking_inquiry", "created_at": days_ago(10)},
        ]
    )


def main() -> None:
    collection = mongomock.MongoClient().db.messages
    seed(collection)

    seven_days_ago = NOW - dt.timedelta(days=7)
    pipeline = [
        {"$match": {"created_at": {"$gte": seven_days_ago}}},
        {
            "$group": {
                "_id": {
                    # $dateToString here == $dateTrunc(unit:"day") on a real server
                    "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "intent": "$intent",
                },
                "count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "day": "$_id.day",
                "intent": "$_id.intent",
                "count": 1,
            }
        },
        {"$sort": {"day": 1, "intent": 1}},
    ]

    rows = list(collection.aggregate(pipeline))

    print("C2 - messages per intent, per day (last 7 days)\n")
    print(f"{'day':<12}{'intent':<22}{'count':>6}")
    print("-" * 40)
    for row in rows:
        print(f"{row['day']:<12}{row['intent']:<22}{row['count']:>6}")

    print("\nNote: the message from 10 days ago is excluded by the $match window.")


if __name__ == "__main__":
    main()
