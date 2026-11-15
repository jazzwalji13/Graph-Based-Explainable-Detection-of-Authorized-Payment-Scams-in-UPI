import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <p className="font-mono text-6xl font-black text-brand">404</p>
      <p className="text-lg font-bold text-ink">This screen doesn't exist.</p>
      <Link to="/" className="rounded-lg bg-brand px-4 py-2 text-sm font-bold text-brandink">Back to the customer app</Link>
    </div>
  );
}
