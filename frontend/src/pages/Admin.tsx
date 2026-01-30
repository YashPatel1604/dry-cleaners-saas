import React from "react";
import { Link } from "react-router-dom";

import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

export default function Admin(): JSX.Element {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.32em] text-muted-foreground/70">
          Admin
        </div>
        <h1 className="text-3xl font-semibold">ADMIN</h1>
        <p className="text-sm text-muted-foreground">
          Manage team settings and tenant configuration.
        </p>
      </div>

      <Card className="glass-panel border-border/70">
        <CardContent className="flex flex-wrap gap-3 p-6">
          <Button asChild size="lg" variant="secondary">
            <Link to="/team">Team</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link to="/invites">Invites</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link to="/settings">Settings</Link>
          </Button>
          <Button asChild size="lg">
            <Link to="/drop">Go to Drop</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
