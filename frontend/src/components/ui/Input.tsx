'use client';

import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  floatingLabel?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      floatingLabel = true,
      type = 'text',
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = useState(false);
    const [isFocused, setIsFocused] = useState(false);
    const [hasValue, setHasValue] = useState(false);

    const inputId = id || `input-${label?.toLowerCase().replace(/\s+/g, '-')}`;
    const isPassword = type === 'password';
    const inputType = isPassword && showPassword ? 'text' : type;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setHasValue(e.target.value.length > 0);
      props.onChange?.(e);
    };

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(true);
      props.onFocus?.(e);
    };

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(false);
      props.onBlur?.(e);
    };

    const containerClasses = `relative ${className}`;

    const inputClasses = `
      w-full px-4 py-3
      ${leftIcon ? 'pl-11' : ''}
      ${rightIcon || isPassword ? 'pr-11' : ''}
      ${floatingLabel && label ? 'pt-6 pb-2' : ''}
      bg-white border-2 rounded-lg
      ${error ? 'border-red-500 focus:border-red-600' : 'border-light-gray focus:border-pinterest-red'}
      ${error ? 'focus:ring-red-500/20' : 'focus:ring-pinterest-red/20'}
      text-charcoal placeholder:text-gray
      transition-all duration-[var(--duration-fast)]
      focus:outline-none focus:ring-4
      disabled:bg-light-gray/50 disabled:cursor-not-allowed
    `.trim().replace(/\s+/g, ' ');

    const labelClasses = `
      absolute left-4
      ${leftIcon ? 'left-11' : 'left-4'}
      transition-all duration-[var(--duration-fast)] pointer-events-none
      ${
        floatingLabel
          ? isFocused || hasValue || props.value
            ? 'top-1.5 text-xs text-pinterest-red'
            : 'top-1/2 -translate-y-1/2 text-base text-gray'
          : 'top-1.5 text-xs text-gray'
      }
    `.trim().replace(/\s+/g, ' ');

    return (
      <div className={containerClasses}>
        {/* Floating or static label */}
        {label && (
          <label htmlFor={inputId} className={labelClasses}>
            {label}
          </label>
        )}

        {/* Left icon */}
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray pointer-events-none">
            {leftIcon}
          </div>
        )}

        {/* Input field */}
        <input
          ref={ref}
          id={inputId}
          type={inputType}
          className={inputClasses}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onChange={handleChange}
          {...props}
        />

        {/* Right icon or password toggle */}
        {isPassword ? (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray hover:text-charcoal transition-colors p-1 rounded focus:outline-none focus:ring-2 focus:ring-pinterest-red"
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        ) : (
          rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray pointer-events-none">
              {rightIcon}
            </div>
          )
        )}

        {/* Error message */}
        {error && (
          <p className="mt-1.5 text-sm text-red-600 animate-slide-down flex items-center gap-1">
            <svg
              className="w-4 h-4"
              fill="currentColor"
              viewBox="0 0 20 20"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            {error}
          </p>
        )}

        {/* Helper text */}
        {helperText && !error && (
          <p className="mt-1.5 text-sm text-gray">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
