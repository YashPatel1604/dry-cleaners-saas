export function stripPhone(value: string): string {
  return value.replace(/\D+/g, "");
}

export function normalizePhoneInput(value: string, maxDigits = 15): string {
  return stripPhone(value).slice(0, maxDigits);
}

export function formatPhoneDisplay(value: string): string {
  const digits = stripPhone(value);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  }
  if (digits.length <= 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)} ${digits.slice(10)}`;
}
