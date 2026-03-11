import { NavLink } from "@/components/NavLink";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <nav className="border-b border-border bg-card px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <NavLink to="/" className="font-mono text-lg font-bold tracking-wider text-primary">
            VOICEOPS
          </NavLink>
          <div className="flex flex-wrap items-center gap-4 sm:gap-6">
            <NavLink
              to="/"
              activeClassName="text-primary border-b-2 border-primary"
              className="font-mono text-xs font-medium tracking-widest text-muted-foreground transition-colors hover:text-foreground pb-1"
            >
              DASHBOARD
            </NavLink>
            <NavLink
              to="/upload"
              activeClassName="text-primary border-b-2 border-primary"
              className="font-mono text-xs font-medium tracking-widest text-muted-foreground transition-colors hover:text-foreground pb-1"
            >
              UPLOAD
            </NavLink>
            <NavLink
              to="/search"
              activeClassName="text-primary border-b-2 border-primary"
              className="font-mono text-xs font-medium tracking-widest text-muted-foreground transition-colors hover:text-foreground pb-1"
            >
              SEARCH
            </NavLink>
            <NavLink
              to="/system"
              activeClassName="text-primary border-b-2 border-primary"
              className="font-mono text-xs font-medium tracking-widest text-muted-foreground transition-colors hover:text-foreground pb-1"
            >
              SYSTEM
            </NavLink>
          </div>
        </div>
      </nav>
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
};

export default Layout;
