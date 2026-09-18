import { useEffect, useState } from "react";
import { fetchStaffList } from "../api/dashboardStaff";
import type { StaffMember } from "../api/dashboardStaff";

export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) {
    return "";
  }
  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase();
  }
  return (words[0].charAt(0) + words[words.length - 1].charAt(0)).toUpperCase();
}

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
    <section className="bg-canvas px-5 py-14 md:px-12">
      <div className="mx-auto max-w-6xl">
        <span className="text-xs font-semibold tracking-widest text-primary uppercase">
          Owner Dashboard
        </span>
        <h2 className="mt-1 text-2xl font-semibold text-ink">
          Staff On Roster
        </h2>
        <ul className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
          {staffMembers.map((staffMember) => (
            <li
              key={staffMember.id}
              className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4 shadow-sm"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary-light text-sm font-semibold text-primary">
                {initials(staffMember.name)}
              </div>
              <div>
                <p className="font-semibold text-ink">{staffMember.name}</p>
                <p className="text-sm text-ink-muted">{staffMember.role}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default StaffList;
