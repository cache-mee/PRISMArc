function StudioInfoSection() {
  return (
    <section className="bg-canvas px-5 py-14 md:px-12">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 lg:grid-cols-2">
        <div>
          <span className="text-xs font-semibold tracking-widest text-primary uppercase">
            Client Words
          </span>
          <h2 className="mt-1 text-2xl font-semibold text-ink">
            Tranquil appointments, redefined.
          </h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <blockquote className="rounded-xl bg-surface p-5 shadow-sm">
              <p className="text-sm text-ink">
                "Booking via chat took twenty seconds while I was walking to my
                car. It understood exactly what I needed."
              </p>
              <footer className="mt-3 text-xs font-semibold text-ink-muted">
                Priya N. — Regular Client
              </footer>
            </blockquote>
            <blockquote className="rounded-xl bg-surface p-5 shadow-sm">
              <p className="text-sm text-ink">
                "No phone calls, no waiting on hold. Best color work I've had in
                the city."
              </p>
              <footer className="mt-3 text-xs font-semibold text-ink-muted">
                Rohan S. — Color &amp; Beard Trim
              </footer>
            </blockquote>
          </div>
        </div>
        <div className="flex flex-col justify-between rounded-2xl bg-primary-light p-8">
          <div>
            <span className="text-xs font-semibold tracking-widest text-primary uppercase">
              Studio Concierge
            </span>
            <h3 className="mt-1 text-xl font-semibold text-ink">
              Salora Salon Flagship
            </h3>
            <p className="mt-2 text-sm text-ink-muted">
              A single-chair boutique salon, run by Ramesh with stylists Meena
              and Arjun.
            </p>
          </div>
          <div className="mt-6 space-y-2 text-sm">
            <div className="flex justify-between rounded-lg bg-surface/70 px-3 py-1.5">
              <span className="text-ink-muted">Tuesday – Saturday</span>
              <span className="font-semibold text-ink">10:00 AM – 8:30 PM</span>
            </div>
            <div className="flex justify-between rounded-lg bg-surface/70 px-3 py-1.5">
              <span className="text-ink-muted">Sunday</span>
              <span className="font-semibold text-ink">10:00 AM – 7:00 PM</span>
            </div>
            <div className="flex justify-between rounded-lg bg-surface/70 px-3 py-1.5">
              <span className="text-ink-muted">Monday</span>
              <span className="font-semibold text-secondary">Closed</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default StudioInfoSection;
