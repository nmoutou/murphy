'use client';

import { createContext, useContext } from 'react';

type Theme = {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    tertiary: string;
    quaternary: string;
  };
};

const darkTheme: Theme = {
  name: 'dark',
  colors: {
    primary: '#0E0D11',
    secondary: '#2a292dff',
    tertiary: '#D9D9D9',
    quaternary: '#FFFFFF',
  },
};

const defaultTheme: Theme = darkTheme;

const ThemeContext = createContext<Theme>(defaultTheme);

export function ThemeProvider({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <ThemeContext.Provider value={defaultTheme}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
