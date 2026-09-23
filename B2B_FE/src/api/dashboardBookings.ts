export type DashboardView = "today" | "week";

export interface BookingEntry {
  staff_name: string;
  customer_name: string;
  service_name: string;
  start_time: string;
}

export async function fetchDashboardBookings(
  view: DashboardView,
): Promise<BookingEntry[]> {
  const response = await fetch(`/dashboard/bookings?view=${view}`);

  if (!response.ok) {
    throw new Error(
      `Dashboard bookings request failed with status ${response.status.toString()}`,
    );
  }

  return (await response.json()) as BookingEntry[];
}
