export interface StaffMember {
  id: string;
  name: string;
  role: string;
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
