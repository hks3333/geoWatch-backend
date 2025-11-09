import React, { HTMLAttributes, InputHTMLAttributes, ButtonHTMLAttributes } from 'react';

const cn = (...classes: (string | boolean | undefined)[]) => classes.filter(Boolean).join(' ');

// Button
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'default' | 'destructive' | 'outline' | 'ghost';
    size?: 'default' | 'sm' | 'lg';
}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'default', size = 'default', ...props }, ref) => {
        const variants = {
            default: 'bg-black text-white hover:bg-gray-800',
            destructive: 'bg-red-600 text-white hover:bg-red-500',
            outline: 'border border-gray-300 bg-transparent hover:bg-gray-100 text-gray-900',
            ghost: 'hover:bg-gray-100 text-gray-900',
        };
        const sizes = {
            default: 'h-10 px-4 py-2',
            sm: 'h-9 rounded-md px-3',
            lg: 'h-11 rounded-md px-8',
        };
        return (
            <button
                className={cn(
                    'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 disabled:pointer-events-none',
                    variants[variant],
                    sizes[size],
                    className
                )}
                ref={ref}
                {...props}
            />
        );
    }
);

// Card
export const Card = React.forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
        <div
            ref={ref}
            className={cn('rounded-xl border bg-white text-gray-900 shadow-sm p-6', className)}
            {...props}
        />
    )
);

// Badge
interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'green' | 'blue' | 'red' | 'yellow';
}
export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
    ({ className, variant = 'default', ...props }, ref) => {
         const variants = {
            default: 'bg-gray-100 text-gray-800',
            green: 'bg-green-100 text-green-800',
            blue: 'bg-blue-100 text-blue-800',
            red: 'bg-red-100 text-red-800',
            yellow: 'bg-yellow-100 text-yellow-800',
        };
        return <div ref={ref} className={cn('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors', variants[variant], className)} {...props} />;
    }
);


// Input
export const Input = React.forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
    ({ className, ...props }, ref) => {
        return (
            <input
                className={cn(
                    'flex h-10 w-full rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
                    className
                )}
                ref={ref}
                {...props}
            />
        );
    }
);

// Skeleton
export const Skeleton = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => {
    return (
        <div
            className={cn('animate-pulse rounded-md bg-gray-200', className)}
            {...props}
        />
    );
};

// Modal
interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
}
export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between p-4 border-b">
                    <h3 className="text-lg font-semibold">{title}</h3>
                    <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-100">&times;</button>
                </div>
                {children}
            </div>
        </div>
    );
};

// RadioGroup
interface RadioGroupContextProps {
  value: string;
  onValueChange: (value: string) => void;
}
const RadioGroupContext = React.createContext<RadioGroupContextProps | null>(null);

// FIX: The RadioGroup component was not rendering its children due to a self-closing div.
// This has been corrected by explicitly destructuring and rendering the children.
export const RadioGroup = ({ value, onValueChange, children, ...props }: { value: string; onValueChange: (value: string) => void; children: React.ReactNode; className?: string }) => {
  return (
    <RadioGroupContext.Provider value={{ value, onValueChange }}>
      <div role="radiogroup" {...props}>
        {children}
      </div>
    </RadioGroupContext.Provider>
  );
};

export const RadioGroupItem = React.forwardRef<HTMLButtonElement, { value: string; id?: string; className?: string }>(({ value, ...props }, ref) => {
  const context = React.useContext(RadioGroupContext);
  if (!context) {
    throw new Error('RadioGroupItem must be used within a RadioGroup');
  }
  const isChecked = context.value === value;
  return (
    <button
      ref={ref}
      type="button"
      role="radio"
      aria-checked={isChecked}
      data-state={isChecked ? 'checked' : 'unchecked'}
      onClick={() => context.onValueChange(value)}
      {...props}
    />
  );
});