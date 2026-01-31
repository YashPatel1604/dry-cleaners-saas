import { useState } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';

export interface CustomerFormData {
  phone: string;
  firstName: string;
  lastName: string;
  email: string;
  address: string;
  preferences: string;
  popUpMessage: string;
}

interface CustomerEditFormProps {
  onSubmit: (data: CustomerFormData) => void;
  onCancel: () => void;
  loading?: boolean;
  error?: string | null;
  initialData?: Partial<CustomerFormData>;
}

interface ValidationErrors {
  phone?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
}

export function CustomerEditForm({
  onSubmit,
  onCancel,
  loading = false,
  error = null,
  initialData,
}: CustomerEditFormProps) {
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
        return value.trim() === '' ? 'First Name is required' : undefined;
      case 'lastName':
        return value.trim() === '' ? 'Last Name is required' : undefined;
      case 'email':
        if (value.trim() === '') return undefined; // Email is optional
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return !emailRegex.test(value) ? 'Invalid email format' : undefined;
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

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
    
    if (!hasErrors) {
      onSubmit(formData);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Phone */}
      <div>
        <Label htmlFor="phone">Phone *</Label>
        <Input
          id="phone"
          type="tel"
          placeholder="(555) 123-4567"
          value={formData.phone}
          onChange={(e) => handleChange('phone', e.target.value)}
          onBlur={() => handleBlur('phone')}
          className={errors.phone && touched.phone ? 'border-red-500' : ''}
        />
        {errors.phone && touched.phone && (
          <p className="text-sm text-red-600 mt-1">{errors.phone}</p>
        )}
      </div>

      {/* First Name */}
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

      {/* Last Name */}
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

      {/* Email */}
      <div>
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="customer@example.com"
          value={formData.email}
          onChange={(e) => handleChange('email', e.target.value)}
          onBlur={() => handleBlur('email')}
          className={errors.email && touched.email ? 'border-red-500' : ''}
        />
        {errors.email && touched.email && (
          <p className="text-sm text-red-600 mt-1">{errors.email}</p>
        )}
      </div>

      {/* Address */}
      <div>
        <Label htmlFor="address">Address</Label>
        <Textarea
          id="address"
          placeholder="Enter customer address"
          value={formData.address}
          onChange={(e) => handleChange('address', e.target.value)}
          rows={3}
        />
      </div>

      {/* Preferences */}
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

      {/* Pop-up Message */}
      <div>
        <Label htmlFor="popUpMessage">Pop-up Message</Label>
        <Textarea
          id="popUpMessage"
          placeholder="Enter pop-up message"
          value={formData.popUpMessage}
          onChange={(e) => handleChange('popUpMessage', e.target.value)}
          rows={3}
        />
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Buttons */}
      <div className="flex gap-3 pt-2">
        <Button type="submit" className="flex-1" disabled={loading}>
          {loading ? 'Saving...' : 'Save Changes'}
        </Button>
        <Button type="button" onClick={onCancel} variant="outline" className="flex-1" disabled={loading}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
