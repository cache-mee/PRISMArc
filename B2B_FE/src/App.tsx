import ChatWindow from "./chat/ChatWindow";
import BookingsList from "./dashboard/BookingsList";
import StaffList from "./dashboard/StaffList";
import Hero from "./shared/Hero";
import ServicesSection from "./shared/ServicesSection";
import StudioInfoSection from "./shared/StudioInfoSection";
import Footer from "./shared/Footer";

function App() {
  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-border bg-surface/80 px-5 py-4 backdrop-blur-md md:px-12">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="text-lg font-semibold tracking-tight text-primary">
            Salora Salon
          </span>
          <span className="hidden text-sm text-ink-muted sm:inline">
            Quiet luxury haircare &amp; sanctuary
          </span>
        </div>
      </header>

      <main>
        <Hero />
        <ServicesSection />
        <StudioInfoSection />
        <StaffList />
        <BookingsList />
      </main>

      <Footer />
      <ChatWindow />
    </div>
  );
}

export default App;
