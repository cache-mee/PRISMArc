import MaterialIcon from "./MaterialIcon";

function Hero() {
  return (
    <section className="bg-canvas px-5 pt-10 pb-14 md:px-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-3">
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-primary-light px-3 py-1 text-xs font-semibold tracking-wide text-primary uppercase">
          <span className="h-2 w-2 rounded-full bg-primary" />
          Bespoke Experience
        </span>
        <h1 className="text-4xl font-bold tracking-tight text-ink md:text-5xl">
          Salora Salon
        </h1>
        <p className="max-w-xl text-base text-ink-muted">
          Effortless hair care and styling, crafted for you — no cumbersome
          forms, just chat with our booking concierge in real time.
        </p>
        <button
          type="button"
          onClick={() => {
            document
              .getElementById("chat-launcher")
              ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
          }}
          className="mt-2 inline-flex w-fit items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-dark"
        >
          <MaterialIcon name="chat_bubble" className="text-[18px]" />
          Start Booking Chat
        </button>
      </div>
    </section>
  );
}

export default Hero;
