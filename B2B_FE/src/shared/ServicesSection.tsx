import MaterialIcon from "./MaterialIcon";

interface ServiceCard {
  icon: string;
  name: string;
  price: string;
  duration: string;
  description: string;
}

const SERVICES: ServiceCard[] = [
  {
    icon: "content_cut",
    name: "Haircut",
    price: "₹300",
    duration: "45 mins",
    description: "A precision cut tailored to your style, finished fresh.",
  },
  {
    icon: "brush",
    name: "Color",
    price: "₹1200",
    duration: "120 mins",
    description: "Full color service with a glossy, salon-fresh finish.",
  },
  {
    icon: "face_3",
    name: "Beard Trim",
    price: "₹150",
    duration: "20 mins",
    description: "A clean, sharp shape-up for a well-groomed look.",
  },
];

function ServicesSection() {
  return (
    <section className="bg-primary-light/40 px-5 py-14 md:px-12">
      <div className="mx-auto max-w-6xl">
        <span className="text-xs font-semibold tracking-widest text-primary uppercase">
          Our Services
        </span>
        <h2 className="mt-1 text-2xl font-semibold text-ink">
          Signature Services &amp; Pricing
        </h2>
        <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-3">
          {SERVICES.map((service) => (
            <div
              key={service.name}
              className="flex flex-col justify-between rounded-2xl border border-border bg-surface p-5 shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-light text-primary">
                    <MaterialIcon name={service.icon} className="text-[20px]" />
                  </div>
                  <span className="text-lg font-bold text-primary">
                    {service.price}
                  </span>
                </div>
                <h3 className="mt-3 text-base font-semibold text-ink">
                  {service.name}
                </h3>
                <p className="mt-1 text-sm text-ink-muted">
                  {service.description}
                </p>
              </div>
              <span className="mt-4 text-xs font-medium text-ink-muted">
                {service.duration}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default ServicesSection;
