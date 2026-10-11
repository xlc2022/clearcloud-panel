export function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <>
      <div className="page-head">
        <h1>{title}</h1>
      </div>
      <div className="card empty">
        <p>{description}</p>
        <p className="muted">Nothing to configure here yet.</p>
      </div>
    </>
  );
}
