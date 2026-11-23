import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

function ActivationArtwork() {
  return (
    <div className="landing-artwork" aria-label="Illustration of an activation moving through review" role="img">
      <div className="art-glow" />
      <div className="art-orbit orbit-a" /><div className="art-orbit orbit-b" />
      <div className="art-board">
        <div className="art-board-top"><span className="art-logo-mark">A</span><span><b>Activation overview</b><small>Campaign workspace</small></span><i>•••</i></div>
        <div className="art-board-stats"><div><small>Active requests</small><b>24</b><span>↑ 12% this month</span></div><div className="art-mini-chart"><i /><i /><i /><i /><i /><i /><i /></div></div>
        <div className="art-board-label">LATEST ACTIVITY <span>View all →</span></div>
        <div className="art-activity"><span className="art-brand brand-blue">F</span><span><b>FizzUp sampling</b><small>Westlands · 14 Jun</small></span><em>Approved</em></div>
        <div className="art-activity"><span className="art-brand brand-yellow">U</span><span><b>Ukulima launch</b><small>Riverside · 18 Jun</small></span><em className="art-pending">In review</em></div>
      </div>
      <div className="art-float art-float-check"><span>✓</span><div><b>AI review complete</b><small>Ready for manager</small></div></div>
      <div className="art-float art-float-calendar"><span>18</span><div><b>Slot reserved</b><small>10:00 – 14:00</small></div></div>
    </div>
  );
}

export default function Landing() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  return (
    <main className="landing-page">
      <header className="landing-nav">
        <Link className="landing-brand" to="/" aria-label="Activation Desk home"><span className="landing-brand-mark">A</span><span>Activation<span className="landing-brand-light">Desk</span></span></Link>
        <nav aria-label="Main navigation"><a href="#how-it-works">How it works</a><Link to="/login">Sign in</Link><Link className="landing-nav-cta" to="/register">Create supplier account <span aria-hidden="true">→</span></Link></nav>
      </header>

      <section className="landing-hero">
        <div className="landing-copy">
          <span className="landing-eyebrow"><i /> CAMPAIGNS, CONNECTED</span>
          <h1>From activation idea to <span>in-store impact.</span></h1>
          <p>Plan brand activations, find the right store slots, and keep every approval moving in one clear workspace.</p>
          <div className="landing-actions"><Link className="landing-primary" to="/register">Get started <span aria-hidden="true">→</span></Link><Link className="landing-secondary" to="/login"><span className="play-icon">▶</span> Sign in to your workspace</Link></div>
          <div className="landing-trust"><div className="trust-avatars"><span>S</span><span>M</span><span>A</span></div><span><b>One shared view</b><small>for suppliers and managers</small></span><i className="trust-divider" /><span className="trust-check">✓</span><span><b>Clear decisions</b><small>at every step</small></span></div>
        </div>
        <ActivationArtwork />
      </section>

      <section className="landing-process" id="how-it-works">
        <div className="process-heading"><span>THE WORKFLOW</span><h2>One process. Everyone in sync.</h2><p>See what’s happening from the first request to the final decision.</p></div>
        <div className="process-cards">
          <article><span className="process-number">01</span><div className="process-icon process-icon-blue">↗</div><h3>Build your activation</h3><p>Choose a brand, store, date and team. Supplier teammates can work from the same workspace.</p></article>
          <article><span className="process-number">02</span><div className="process-icon process-icon-yellow">✦</div><h3>Get a guided review</h3><p>Automated checks highlight request quality and potential conflicts for the review team.</p></article>
          <article><span className="process-number">03</span><div className="process-icon process-icon-green">✓</div><h3>Track the decision</h3><p>Follow approvals, changes and booked activations without losing the request history.</p></article>
        </div>
      </section>

      <footer className="landing-footer"><Link className="landing-brand" to="/"><span className="landing-brand-mark">A</span><span>Activation<span className="landing-brand-light">Desk</span></span></Link><span>Make every activation easier to run.</span><Link to="/login">Open your workspace →</Link></footer>
    </main>
  );
}
