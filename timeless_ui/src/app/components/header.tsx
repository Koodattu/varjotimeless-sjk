"use client";

import Image from "next/image";
import styles from "@/app/styles/header.module.css"; 

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <Image src="/logo/timeless_logo-removebg.png" alt="Logo" width={50} height={50} />
      </div>

      <h1 className={styles.title}>TimeLess</h1>

      <div className={styles.spacer}></div>
    </header>
  );
}
