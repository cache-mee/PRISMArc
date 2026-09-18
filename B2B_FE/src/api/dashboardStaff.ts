export interface StaffMember {
  staff_id: number;
  staff_name: string;
  role: string;
  blocked: boolean;
  today_booking_count: number;
}

export async function fetchStaffList(): Promise<StaffMember[]> {
  const response = await fetch("/dashboard/staff");

  if (!response.ok) {
    throw new Error(
      `Staff list request failed with status ${response.status.toString()}`,
    );
  }

  return (await response.json()) as StaffMember[];
}
