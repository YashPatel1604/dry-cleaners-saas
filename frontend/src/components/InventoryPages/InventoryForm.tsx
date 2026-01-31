import { useState } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';

export interface InventoryFormData {
  name: string;
  sku: string;
  price: string;
  category: string;
  active: boolean;
}

interface InventoryFormProps {
  onSubmit: (data: InventoryFormData) => void;
  onCancel: () => void;
  loading?: boolean;
  error?: string | null;
  initialData?: Partial<InventoryFormData>;
}

interface ValidationErrors {
  name?: string;
  price?: string;
}

export function InventoryForm({
  onSubmit,
  onCancel,
  loading = false,
  error = null,
  initialData,
}: InventoryFormProps) {
  const [formData, setFormData] = useState<InventoryFormData>({
    name: initialData?.name || '',
    sku: initialData?.sku || '',
    price: initialData?.price || '',
    category: initialData?.category || '',
    active: initialData?.active !== undefined ? initialData.active : true,
  });

  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateField = (name: keyof InventoryFormData, value: string | boolean): string | undefined => {
    switch (name) {
      case 'name':
        return typeof value === 'string' && value.trim() === '' ? 'Item Name is required' : undefined;
      case 'price':
        if (typeof value === 'string') {
          if (value.trim() === '') return 'Price is required';
          if (isNaN(Number(value)) || Number(value) < 0) return 'Price must be a valid number';
        }
        return undefined;
      default:
        return undefined;
    }
  };

  const handleChange = (name: keyof InventoryFormData, value: string | boolean) => {
    setFormData({ ...formData, [name]: value });
    
    if (touched[name]) {
      const error = validateField(name, value);
      setErrors({ ...errors, [name]: error });
    }
  };

  const handleBlur = (name: keyof InventoryFormData) => {
    setTouched({ ...touched, [name]: true });
    const error = validateField(name, formData[name]);
    setErrors({ ...errors, [name]: error });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate all required fields
    const newErrors: ValidationErrors = {
      name: validateField('name', formData.name),
      price: validateField('price', formData.price),
    };

    setErrors(newErrors);
    setTouched({
      name: true,
      price: true,
    });

    // Check if there are any errors
    const hasErrors = Object.values(newErrors).some(error => error !== undefined);
    
    if (!hasErrors) {
      onSubmit(formData);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Item Name */}
      <div>
        <Label htmlFor="name">Item Name *</Label>
        <Input
          id="name"
          type="text"
          placeholder="Enter item name"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          onBlur={() => handleBlur('name')}
          className={errors.name && touched.name ? 'border-red-500' : ''}
        />
        {errors.name && touched.name && (
          <p className="text-sm text-red-600 mt-1">{errors.name}</p>
        )}
      </div>

      {/* SKU */}
      <div>
        <Label htmlFor="sku">SKU</Label>
        <Input
          id="sku"
          type="text"
          placeholder="Enter SKU"
          value={formData.sku}
          onChange={(e) => handleChange('sku', e.target.value)}
        />
      </div>

      {/* Price */}
      <div>
        <Label htmlFor="price">Price *</Label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
          <Input
            id="price"
            type="number"
            step="0.01"
            placeholder="0.00"
            value={formData.price}
            onChange={(e) => handleChange('price', e.target.value)}
            onBlur={() => handleBlur('price')}
            className={`pl-7 ${errors.price && touched.price ? 'border-red-500' : ''}`}
          />
        </div>
        {errors.price && touched.price && (
          <p className="text-sm text-red-600 mt-1">{errors.price}</p>
        )}
      </div>

      {/* Category */}
      <div>
        <Label htmlFor="category">Category</Label>
        <Input
          id="category"
          type="text"
          placeholder="Enter category"
          value={formData.category}
          onChange={(e) => handleChange('category', e.target.value)}
        />
      </div>

      {/* Active Toggle */}
      <div className="flex items-center justify-between">
        <Label htmlFor="active" className="cursor-pointer">Active</Label>
        <Switch
          id="active"
          checked={formData.active}
          onCheckedChange={(checked) => handleChange('active', checked)}
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
          {loading ? 'Saving...' : 'SAVE'}
        </Button>
        <Button type="button" onClick={onCancel} variant="outline" className="flex-1" disabled={loading}>
          CANCEL
        </Button>
      </div>
    </form>
  );
}
