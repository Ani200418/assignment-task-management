import { redirect } from "next/navigation";

export default function Home() {
  redirect("/dashboard"); // the (app) layout sends signed-out visitors on to /login
}
