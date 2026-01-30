import React from "react";
import { Link } from "react-router-dom";

import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

export default function Extras(): JSX.Element {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.32em] text-muted-foreground/70">
          Tools
        </div>
        <h1 className="text-3xl font-semibold">EXTRAS</h1>
        <p className="text-sm text-muted-foreground">
          Quick shortcuts to supporting tools.
        </p>
      </div>

      <Card className="glass-panel border-border/70">
        <CardContent className="flex flex-wrap gap-3 p-6">
          <Button asChild size="lg" variant="secondary">
            <Link to="/inventory">Inventory</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link to="/reports">Reports</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link to="/queue">Queue</Link>
          </Button>
          <Button asChild size="lg">
            <Link to="/drop">Go to Drop</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
