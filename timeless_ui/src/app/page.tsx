import styles from "./styles/page.module.css";
import ProjectDataWrapper from "./components/projectDataProvider";
import Header from "./components/header";

export default function Home() {
  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.main}>
        <ProjectDataWrapper />
      </main>
      {/* <footer className={styles.footer}>
        <div>FOOTER</div>
      </footer> */}
    </div>
  );
}
