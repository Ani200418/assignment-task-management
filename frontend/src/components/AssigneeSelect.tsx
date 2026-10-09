import type { SelectHTMLAttributes } from "react";
import type { Profile } from "@/types/api";
import { inputClass } from "./ui";

type Props = SelectHTMLAttributes<HTMLSelectElement> & { users: Profile[]; currentUserId?: string };

/** Shows name + email of registered users. Value "" means unassigned. */
export function AssigneeSelect({ users, currentUserId, ...rest }: Props) {
  return (
    <select {...rest} className={inputClass}>
      <option value="">Unassigned</option>
      {users.map((u) => (
        <option key={u.id} value={u.id}>
          {(u.full_name || u.email) + (u.full_name ? ` (${u.email})` : "") + (u.id === currentUserId ? " - you" : "")}
        </option>
      ))}
    </select>
  );
}
