import { useEffect, useState } from "react";
import { fetchStaffList } from "../api/dashboardStaff";
import type { StaffMember } from "../api/dashboardStaff";

function StaffList() {
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([]);

  useEffect(() => {
    fetchStaffList()
      .then((response) => {
        setStaffMembers(response);
      })
      .catch((error: unknown) => {
        console.error("Failed to load staff list", error);
      });
  }, []);

  return (
    <section>
      <ul>
        {staffMembers.map((staffMember) => (
          <li key={staffMember.id}>
            {staffMember.name} &mdash; {staffMember.role}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default StaffList;
