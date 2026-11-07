import { z } from 'zod'

// Mirrors backend/app/schemas/validators.py (FR-PRO-03).

export const phoneSchema = z
  .string()
  .trim()
  .transform((v) => v.replace(/[\s\-().]/g, ''))
  .pipe(z.string().regex(/^\+?[0-9]{9,15}$/, 'Phone number must contain 9-15 digits and may start with +.'))

export const fullNameSchema = z.string().trim().min(2, 'Please enter your full name.').max(100)

export const dateOfBirthSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, 'Please enter a valid date.')
  .refine((v) => new Date(v) < new Date(), 'Date of birth must be in the past.')

/** Optional fields: an empty input is allowed and means "not provided". */
export const optionalDateOfBirthSchema = z.union([z.literal(''), dateOfBirthSchema])
export const optionalPhoneSchema = z.union([z.literal(''), phoneSchema])

export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters.')
  .max(128)
  .refine((v) => /[A-Za-z]/.test(v) && /\d/.test(v), 'Password must contain at least one letter and one digit.')

export const registerSchema = z
  .object({
    email: z.string().trim().email('Please enter a valid email.'),
    password: passwordSchema,
    confirm_password: z.string(),
    full_name: fullNameSchema,
    date_of_birth: optionalDateOfBirthSchema,
    phone_number: optionalPhoneSchema,
  })
  .refine((v) => v.password === v.confirm_password, { message: 'Passwords do not match.', path: ['confirm_password'] })

export const profileSchema = z.object({
  full_name: fullNameSchema,
  date_of_birth: optionalDateOfBirthSchema,
  phone_number: optionalPhoneSchema,
  address: z.string().trim().max(255).optional(),
})

export const reviewSchema = z.object({
  rating: z.number().int().min(1, 'Please choose a rating.').max(5),
  comment: z.string().trim().max(2000).optional(),
})
