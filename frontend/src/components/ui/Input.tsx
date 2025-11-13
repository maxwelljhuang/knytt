'use client';

import React, { useState, useEffect } from 'react';
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
    const inputRef = React.useRef<HTMLInputElement | null>(null);

    // Combine refs
    const setRefs = React.useCallback(
      (element: HTMLInputElement | null) => {
        inputRef.current = element;
        if (typeof ref === 'function') {
          ref(element);
        } else if (ref) {
          ref.current = element;
        }
      },
      [ref]
    );

    // Check for value on mount and when props change
    useEffect(() => {
      const inputElement = inputRef.current;
      if (!inputElement) return;

      const checkValue = () => {
        if (inputElement) {
          setHasValue(inputElement.value.length > 0);
        }
      };

      checkValue();

      // Multiple checks to catch autocomplete and password managers
      const timer1 = setTimeout(checkValue, 100);
      const timer2 = setTimeout(checkValue, 300);
      const timer3 = setTimeout(checkValue, 500);
      const timer4 = setTimeout(checkValue, 1000); // Extra check for slow password managers

      // Listen for input events to catch browser autofill
      const handleInput = () => {
        checkValue();
      };

      inputElement.addEventListener('input', handleInput);
      inputElement.addEventListener('change', handleInput);

      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
        clearTimeout(timer3);
        clearTimeout(timer4);
        inputElement.removeEventListener('input', handleInput);
        inputElement.removeEventListener('change', handleInput);
      };
    }, [props.value, props.defaultValue]);

    // Additional check on every render to catch browser-filled values
    useEffect(() => {
      if (inputRef.current && inputRef.current.value.length > 0 && !hasValue) {
        setHasValue(true);
      }
    });

    const inputId = id || `input-${label?.toLowerCase().replace(/\s+/g, '-')}`;
    const isPassword = type === 'password';
    const inputType = isPassword && showPassword ? 'text' : type;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const hasContent = e.target.value.length > 0;
      setHasValue(hasContent);
      props.onChange?.(e);
    };

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(true);
      // Check value on focus
      setHasValue(e.target.value.length > 0);
      props.onFocus?.(e);
    };

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(false);
      // Check value on blur
      setHasValue(e.target.value.length > 0);
      props.onBlur?.(e);
    };

    const containerClasses = `relative ${className}`;

    const inputClasses = `
      w-full px-4
      ${leftIcon ? 'pl-11' : ''}
      ${rightIcon || isPassword ? 'pr-11' : ''}
      ${floatingLabel && label ? 'pt-6 pb-3' : 'py-3'}
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
            : 'top-[28px] -translate-y-1/2 text-base text-gray'
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
          <div className={`absolute left-3 text-gray pointer-events-none ${
            floatingLabel && label ? 'top-[28px] -translate-y-1/2' : 'top-1/2 -translate-y-1/2'
          }`}>
            {leftIcon}
          </div>
        )}

        {/* Input field */}
        <input
          ref={setRefs}
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
            className={`absolute right-3 text-gray hover:text-charcoal transition-colors p-1 rounded focus:outline-none focus:ring-2 focus:ring-pinterest-red ${
              floatingLabel && label ? 'top-[28px] -translate-y-1/2' : 'top-1/2 -translate-y-1/2'
            }`}
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        ) : (
          rightIcon && (
            <div className={`absolute right-3 text-gray pointer-events-none ${
              floatingLabel && label ? 'top-[28px] -translate-y-1/2' : 'top-1/2 -translate-y-1/2'
            }`}>
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
