import { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { AdminSectionHeader } from './AdminSectionHeader';
import { AdminSettingField } from './AdminSettingField';
import { AdminToggleField } from './AdminToggleField';
import { AdminErrorState } from './AdminErrorState';
import { Card } from '../ui/card';
import { Separator } from '../ui/separator';

interface Settings {
  default_turnaround_days: number;
  default_ready_hour: number;
  default_ready_minute: number;
  require_paid_in_full_at_pickup: boolean;
  collects_tax: boolean;
  tax_rate_bps: number;
}

interface AdminSettingsSectionProps {
  settings: Settings;
  onSave: (settings: Settings) => void;
  saving?: boolean;
  error?: string | null;
}

export function AdminSettingsSection({
  settings,
  onSave,
  saving = false,
  error = null,
}: AdminSettingsSectionProps) {
  const [localSettings, setLocalSettings] = useState(settings);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  useEffect(() => {
    const isDifferent = JSON.stringify(localSettings) !== JSON.stringify(settings);
    setHasChanges(isDifferent);
  }, [localSettings, settings]);

  const handleSave = () => {
    onSave(localSettings);
  };

  if (error) {
    return <AdminErrorState error={error} />;
  }

  return (
    <div>
      <AdminSectionHeader
        title="Settings"
        description="Configure store defaults and preferences"
        action={
          <Button onClick={handleSave} disabled={!hasChanges || saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        }
      />

      <Card className="p-6 space-y-6">
        {/* Order Defaults */}
        <div>
          <h3 className="text-lg text-gray-800 mb-4">Order Defaults</h3>
          <div className="space-y-4">
            <AdminSettingField
              id="turnaround_days"
              label="Default Turnaround Days"
              value={localSettings.default_turnaround_days}
              onChange={(value) =>
                setLocalSettings({
                  ...localSettings,
                  default_turnaround_days: parseInt(value) || 0,
                })
              }
              type="number"
              description="Number of days until order is ready for pickup"
            />

            <div className="grid grid-cols-2 gap-4 max-w-md">
              <AdminSettingField
                id="ready_hour"
                label="Ready Hour"
                value={localSettings.default_ready_hour}
                onChange={(value) =>
                  setLocalSettings({
                    ...localSettings,
                    default_ready_hour: parseInt(value) || 0,
                  })
                }
                type="number"
                description="24-hour format (0-23)"
              />

              <AdminSettingField
                id="ready_minute"
                label="Ready Minute"
                value={localSettings.default_ready_minute}
                onChange={(value) =>
                  setLocalSettings({
                    ...localSettings,
                    default_ready_minute: parseInt(value) || 0,
                  })
                }
                type="number"
                description="Minutes (0-59)"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Payment Settings */}
        <div>
          <h3 className="text-lg text-gray-800 mb-4">Payment Settings</h3>
          <div className="space-y-2">
            <AdminToggleField
              id="require_paid_in_full"
              label="Require Paid in Full at Pickup"
              checked={localSettings.require_paid_in_full_at_pickup}
              onCheckedChange={(checked) =>
                setLocalSettings({
                  ...localSettings,
                  require_paid_in_full_at_pickup: checked,
                })
              }
              description="Customers must pay the full amount before picking up orders"
            />
          </div>
        </div>

        <Separator />

        {/* Tax Settings */}
        <div>
          <h3 className="text-lg text-gray-800 mb-4">Tax Settings</h3>
          <div className="space-y-4">
            <AdminToggleField
              id="collects_tax"
              label="Collect Sales Tax"
              checked={localSettings.collects_tax}
              onCheckedChange={(checked) =>
                setLocalSettings({
                  ...localSettings,
                  collects_tax: checked,
                })
              }
              description="Enable sales tax collection on orders"
            />

            {localSettings.collects_tax && (
              <AdminSettingField
                id="tax_rate"
                label="Tax Rate (basis points)"
                value={localSettings.tax_rate_bps}
                onChange={(value) =>
                  setLocalSettings({
                    ...localSettings,
                    tax_rate_bps: parseInt(value) || 0,
                  })
                }
                type="number"
                description="Tax rate in basis points (e.g., 850 = 8.5%)"
              />
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
