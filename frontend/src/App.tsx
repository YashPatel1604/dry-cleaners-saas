import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-6">
      <Card className="w-full max-w-md">
        <CardContent className="p-6 space-y-5">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Dry Cleaners SaaS
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Milestone M1: Django API + React UI scaffold
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" placeholder="owner@location.com" />
          </div>

          <Button className="w-full">Continue</Button>
        </CardContent>
      </Card>
    </div>
  );
}
