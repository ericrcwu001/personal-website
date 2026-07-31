export function SiteNav() {
  return (
    <nav className="site-nav" aria-label="Primary navigation">
      <a className="wordmark" href="/" aria-label="Eric Wu home">
        Eric Wu
      </a>
      <div className="nav-links">
        <a href="/#projects">Projects</a>
        <a href="mailto:ericrcwu@stanford.edu">Email</a>
        <a href="/Eric_Wu_CV.pdf">Resume</a>
      </div>
    </nav>
  );
}
