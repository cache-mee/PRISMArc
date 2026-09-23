import { useEffect, useState } from "react";
import { fetchDashboardBookings } from "../api/dashboardBookings";
import type { BookingEntry, DashboardView } from "../api/dashboardBookings";

function formatStartTime(startTime: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(startTime));
}

function groupByStaffName(
  bookings: BookingEntry[],
): Map<string, BookingEntry[]> {
  const groups = new Map<string, BookingEntry[]>();

  for (const booking of bookings) {
    const existing = groups.get(booking.staff_name);
    if (existing) {
      existing.push(booking);
    } else {
      groups.set(booking.staff_name, [booking]);
    }
  }

  return groups;
}

function BookingsList() {
  const [bookings, setBookings] = useState<BookingEntry[]>([]);
  const [view, setView] = useState<DashboardView>("today");

  useEffect(() => {
    fetchDashboardBookings(view)
      .then((response) => {
        setBookings(response);
      })
      .catch((error: unknown) => {
        console.error("Failed to load dashboard bookings", error);
      });
  }, [view]);

  const groupedBookings = groupByStaffName(bookings);

  return (
    <section className="bg-canvas px-5 py-14 md:px-12">
      <div className="mx-auto max-w-6xl">
        <span className="text-xs font-semibold tracking-widest text-primary uppercase">
          Owner Dashboard
        </span>
        <h2 className="mt-1 text-2xl font-semibold text-ink">Bookings</h2>

        <div className="mt-4 inline-flex rounded-full border border-border bg-surface p-1">
          <button
            type="button"
            onClick={() => {
              setView("today");
            }}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
              view === "today"
                ? "bg-primary-light text-primary"
                : "text-ink-muted"
            }`}
          >
            Today
          </button>
          <button
            type="button"
            onClick={() => {
              setView("week");
            }}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
              view === "week"
                ? "bg-primary-light text-primary"
                : "text-ink-muted"
            }`}
          >
            This Week
          </button>
        </div>

        {groupedBookings.size === 0 ? (
          <p className="mt-6 text-sm text-ink-muted">No bookings</p>
        ) : (
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
            {Array.from(groupedBookings.entries()).map(
              ([staffName, staffBookings]) => (
                <div
                  key={staffName}
                  className="rounded-2xl border border-border bg-surface p-4 shadow-sm"
                >
                  <p className="font-semibold text-ink">{staffName}</p>
                  <ul className="mt-2 space-y-2">
                    {staffBookings.map((booking) => (
                      <li
                        key={`${booking.staff_name}-${booking.start_time}-${booking.customer_name}`}
                        className="text-sm text-ink-muted"
                      >
                        <span className="text-ink">
                          {booking.customer_name}
                        </span>{" "}
                        &mdash; {booking.service_name} &middot;{" "}
                        {formatStartTime(booking.start_time)}
                      </li>
                    ))}
                  </ul>
                </div>
              ),
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default BookingsList;
