<p align="center">
    <a href="https://github.com/SilentDemonSD/WZML-X">
        <kbd>
            <img width="250" src="https://graph.org/file/639fe4239b78e5862b302.jpg" alt="WZML-X Logo">
        </kbd>
    </a>

<i>This repository is a feature-enhanced version of the [mirror-leech-telegram-bot](https://github.com/anasty17/mirror-leech-telegram-bot). It integrates various improvements from multiple sources, expanding functionality while maintaining efficiency. Unlike the base repository, this version is fully deployable on Heroku.</i>

</p>

<div align=center>

[![](https://img.shields.io/github/repo-size/weebzone/WZML-X?color=green&label=Repo%20Size&labelColor=292c3b)](#) [![](https://img.shields.io/github/commit-activity/m/weebzone/WZML-X?logo=github&labelColor=292c3b&label=Github%20Commits)](#) [![](https://img.shields.io/github/license/weebzone/WZML-X?style=flat&label=License&labelColor=292c3b)](#)|[![](https://img.shields.io/github/issues-raw/weebzone/WZML-X?style=flat&label=Open%20Issues&labelColor=292c3b)](#) [![](https://img.shields.io/github/issues-closed-raw/weebzone/WZML-X?style=flat&label=Closed%20Issues&labelColor=292c3b)](#) [![](https://img.shields.io/github/issues-pr-raw/weebzone/WZML-X?style=flat&label=Open%20Pull%20Requests&labelColor=292c3b)](#) [![](https://img.shields.io/github/issues-pr-closed-raw/weebzone/WZML-X?style=flat&label=Closed%20Pull%20Requests&labelColor=292c3b)](#)
:---:|:---:|
[![](https://img.shields.io/github/languages/count/weebzone/WZML-X?style=flat&label=Total%20Languages&labelColor=292c3b&color=blueviolet)](#) [![](https://img.shields.io/github/languages/top/weebzone/WZML-X?style=flat&logo=python&labelColor=292c3b)](#) [![](https://img.shields.io/github/last-commit/weebzone/WZML-X?style=flat&label=Last%20Commit&labelColor=292c3b&color=important)](#) [![](https://badgen.net/github/branches/weebzone/WZML-X?label=Total%20Branches&labelColor=292c3b)](#)|[![](https://img.shields.io/github/forks/weebzone/WZML-X?style=flat&logo=github&label=Forks&labelColor=292c3b&color=critical)](#) [![](https://img.shields.io/github/stars/weebzone/WZML-X?style=flat&logo=github&label=Stars&labelColor=292c3b&color=yellow)](#) [![](https://badgen.net/docker/pulls/codewithweeb/weebzone?icon=docker&label=Pulls&labelColor=292c3b&color=blue)](#)
[![](https://img.shields.io/badge/Telegram%20Channel-Join-9cf?style=for-the-badge&logo=telegram&logoColor=blue&style=flat&labelColor=292c3b)](https://t.me/WZML_X) |[![](https://img.shields.io/badge/Support%20Group-Join-9cf?style=for-the-badge&logo=telegram&logoColor=blue&style=flat&labelColor=292c3b)](https://t.me/WZML_Support) |

</div>

---
Below is a refined version that preserves all the important details while enhancing readability and design :

---

# Deployment Guide (VPS)

<details>
  <summary><strong>View All Steps <kbd>Click Here</kbd></strong></summary>

---

## 1. Prerequisites

- **Tutorial Video from A to Z (Latest Video)**
- Special thanks to [Wiszky](https://github.com/vishnoe115)

[![See Video](https://img.shields.io/badge/See%20Video-black?style=for-the-badge&logo=YouTube)](https://youtu.be/xzLOLyKYl54)

---

## 2. Installing Requirements

Clone this repository:

```bash
git clone https://github.com/SilentDemonSD/WZML-X mirrorbot/ && cd mirrorbot
```

---

## 3. Build and Run the Docker Image

*Make sure you mount the app folder and install Docker following the official documentation.*

There are two methods to build and run the Docker image:

### 3.1 Using Official Docker Commands

- **Start Docker daemon** (skip if already running):

  ```bash
  sudo dockerd
  ```

- **Build the Docker image:**

  ```bash
  sudo docker build . -t wzmlx
  ```

- **Run the image:**

  ```bash
  sudo docker run -p 80:80 -p 8080:8080 wzmlx
  ```

- **To stop the running image:**

  First, list running containers:

  ```bash
  sudo docker ps
  ```

  Then, stop the container using its ID:

  ```bash
  sudo docker stop <container_id>
  ```

---

### 3.2 Using docker-compose (Recommended)

**Note:** If you want to use ports other than 80 and 8080 for torrent file selection and rclone serve respectively, update them in [docker-compose.yml](https://github.com/weebzone/WZML-X/blob/master/docker-compose.yml).

- **Install docker-compose:**

  ```bash
  sudo apt install docker-compose
  ```

- **Build and run the Docker image (or view the current running image):**

  ```bash
  sudo docker-compose up
  ```

- **After editing files (e.g., using nano to edit start.sh), rebuild:**

  ```bash
  sudo docker-compose up --build
  ```

- **To stop the running image:**

  ```bash
  sudo docker-compose stop
  ```

- **To restart the image:**

  ```bash
  sudo docker-compose start
  ```

- **To view the latest logs from the running container (after mounting the folder):**

  ```bash
  sudo docker-compose up
  ```

- **Tutorial Video for docker-compose and checking ports:**

  [![See Video](https://img.shields.io/badge/See%20Video-black?style=for-the-badge&logo=YouTube)](https://youtu.be/c8_TU1sPK08)


------

#### Docker Notes

**IMPORTANT NOTES**:

1. Set `BASE_URL_PORT` and `RCLONE_SERVE_PORT` variables to any port you want to use. Default is `80` and `8080` respectively.
2. You should stop the running image before deleting the container and you should delete the container before the image.
3. To delete the container (this will not affect on the image):

```
sudo docker container prune
```

4. To delete te images:

```
sudo docker image prune -a
```

5. Check the number of processing units of your machine with `nproc` cmd and times it by 4, then edit `AsyncIOThreadsCount` in qBittorrent.conf.
    
  </details></li></ol>
</details>
    
------

# Deployment Guide (Heroku)

<details>
  <summary><strong>View All Steps <kbd>Click Here</kbd></strong></summary>

---

**Check the Docs Here :** [Click Here](https://github.com/SilentDemonSD/WZ-Deploy/tree/main?tab=readme-ov-file#2%EF%B8%8F⃣-method-2-github-workflow-guide)

---

</details>

## 🏅 **Bot Authors**
<details>
    <summary><b>Click Here For Description</b></summary>

|<img width="80" src="https://avatars.githubusercontent.com/u/105407900">|<img width="80" src="https://avatars.githubusercontent.com/u/113664541">|<img width="80" src="https://avatars.githubusercontent.com/u/84721324">|
|:---:|:---:|:---:|
|[`SilentDemonSD`](https://github.com/SilentDemonSD)|[`CodeWithWeeb`](https://github.com/weebzone)|[`Maverick`](https://github.com/MajnuRangeela)|
|Author and DDL, UI Design, More Customs..|Author and Wraps Up Features|Co-Author & Bug Tester|

</details>

