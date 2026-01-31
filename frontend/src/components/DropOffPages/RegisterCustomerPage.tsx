import { useState } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import { Card } from '../ui/card';

interface RegisterCustomerPageProps {
  onSave?: (customerData: CustomerFormData) => void;
  onCancel?: () => void;
  initialData?: Partial<CustomerFormData>;
}

export interface CustomerFormData {
  phone: string;
  firstName: string;
  lastName: string;
  email: string;
  address: string;
  preferences: string;
  popUpMessage: string;
}

interface ValidationErrors {
  phone?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
}

export function RegisterCustomerPage({
  onSave,
  onCancel,
  initialData,
}: RegisterCustomerPageProps) {
  const [formData, setFormData] = useState<CustomerFormData>({
    phone: initialData?.phone || '',
    firstName: initialData?.firstName || '',
    lastName: initialData?.lastName || '',
    email: initialData?.email || '',
    address: initialData?.address || '',
    preferences: initialData?.preferences || '',
    popUpMessage: initialData?.popUpMessage || '',
  });

  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateField = (name: keyof CustomerFormData, value: string): string | undefined => {
    switch (name) {
      case 'phone':
        return value.trim() === '' ? 'Phone is required' : undefined;
      case 'firstName':
        return value.trim() === '' ? 'First name is required' : undefined;
      case 'lastName':
        return value.trim() === '' ? 'Last name is required' : undefined;
      case 'email':
        if (value.trim() !== '' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          return 'Invalid email format';
        }
        return undefined;
      default:
        return undefined;
    }
  };

  const handleChange = (name: keyof CustomerFormData, value: string) => {
    setFormData({ ...formData, [name]: value });
    
    if (touched[name]) {
      const error = validateField(name, value);
      setErrors({ ...errors, [name]: error });
    }
  };

  const handleBlur = (name: keyof CustomerFormData) => {
    setTouched({ ...touched, [name]: true });
    const error = validateField(name, formData[name]);
    setErrors({ ...errors, [name]: error });
  };

  const handleSave = () => {
    // Validate all required fields
    const newErrors: ValidationErrors = {
      phone: validateField('phone', formData.phone),
      firstName: validateField('firstName', formData.firstName),
      lastName: validateField('lastName', formData.lastName),
      email: validateField('email', formData.email),
    };

    setErrors(newErrors);
    setTouched({
      phone: true,
      firstName: true,
      lastName: true,
      email: true,
    });

    // Check if there are any errors
    const hasErrors = Object.values(newErrors).some(error => error !== undefined);
    
    if (!hasErrors && onSave) {
      onSave(formData);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl mb-8 text-gray-800">Register</h1>

      <Card className="p-8">
        <div className="space-y-6">
          <div>
            <Label htmlFor="phone">Phone *</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="Enter phone number"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              onBlur={() => handleBlur('phone')}
              className={errors.phone && touched.phone ? 'border-red-500' : ''}
            />
            {errors.phone && touched.phone && (
              <p className="text-sm text-red-600 mt-1">{errors.phone}</p>
            )}
          </div>

          <div>
            <Label htmlFor="firstName">First Name *</Label>
            <Input
              id="firstName"
              type="text"
              placeholder="Enter first name"
              value={formData.firstName}
              onChange={(e) => handleChange('firstName', e.target.value)}
              onBlur={() => handleBlur('firstName')}
              className={errors.firstName && touched.firstName ? 'border-red-500' : ''}
            />
            {errors.firstName && touched.firstName && (
              <p className="text-sm text-red-600 mt-1">{errors.firstName}</p>
            )}
          </div>

          <div>
            <Label htmlFor="lastName">Last Name *</Label>
            <Input
              id="lastName"
              type="text"
              placeholder="Enter last name"
              value={formData.lastName}
              onChange={(e) => handleChange('lastName', e.target.value)}
              onBlur={() => handleBlur('lastName')}
              className={errors.lastName && touched.lastName ? 'border-red-500' : ''}
            />
            {errors.lastName && touched.lastName && (
              <p className="text-sm text-red-600 mt-1">{errors.lastName}</p>
            )}
          </div>

          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="Enter email address"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              onBlur={() => handleBlur('email')}
              className={errors.email && touched.email ? 'border-red-500' : ''}
            />
            {errors.email && touched.email && (
              <p className="text-sm text-red-600 mt-1">{errors.email}</p>
            )}
          </div>

          <div>
            <Label htmlFor="address">Address</Label>
            <Textarea
              id="address"
              placeholder="Enter address"
              value={formData.address}
              onChange={(e) => handleChange('address', e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="preferences">Preferences</Label>
            <Textarea
              id="preferences"
              placeholder="Enter customer preferences"
              value={formData.preferences}
              onChange={(e) => handleChange('preferences', e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="popUpMessage">Pop‑up Message</Label>
            <Textarea
              id="popUpMessage"
              placeholder="Enter pop-up message"
              value={formData.popUpMessage}
              onChange={(e) => handleChange('popUpMessage', e.target.value)}
              rows={3}
            />
          </div>

          <div className="flex gap-3 pt-4">
            <Button onClick={handleSave} className="flex-1">
              SAVE
            </Button>
            <Button onClick={handleCancel} variant="outline" className="flex-1">
              CANCEL
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
