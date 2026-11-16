# UAAF Social Publisher launch guide

## Direction

**Keep the name UAAF Social Publisher.** Use “Publish short videos from your own setup.” as the main line. Lead with the job the tool does. The primary reader is a technical creator or developer with an existing short-video workflow.

**GitHub About**  
Self-hosted Python toolkit for short-form video publishing, with local video checks and social platform adapters.

**Topics**  
`social-media-automation`, `video-publishing`, `short-form-video`, `python`, `ffmpeg`, `self-hosted`

The visual system uses deep ink `#17141F`, lilac `#CBB5FF`, peach `#FFAB7C`, and warm white `#F7F4EE`. Use bold, readable sans-serif headlines and mono text for commands and measured output. The play mark anchors the wordmark. The layered video cards show one clip fanning out to several destinations. The artwork is an illustration. The replay uses actual validator results.

BeyondSEO is the model for the reading order. It leads with a benefit, supplies an illustrated workflow, offers a concrete way to try the project, and shows a real output example. Use those same jobs for each section of UAAF's page. [BeyondSEO repository](https://github.com/beyondtahir/beyondseo)

## What to do in order

1. **Put up the new README and social preview.** Copy the supplied README, media and sample clip into the repository. Check the README on a phone. Set the description and topics above. Upload `uaaf-social-preview.jpg` under **Settings → Social preview**. The card is 1280×640 and under 1 MB. [GitHub social preview docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
2. **Make the first install repeatable.** Have two testers use a clean checkout, ideally one on Windows and one on macOS or Linux. Ask them to run the local check without coaching. Record time to first result and every failure. Add automated coverage for vertical, landscape, missing-file and unreadable-file cases if this becomes the primary starter workflow.
3. **Audit the first full publishing path.** Choose the channel where you already have suitable API access. Publish a test clip to your own account and record the exact repeatable setup, permissions, outcome, and date. Check what works from a fresh clone, including optional imports and cloud dependencies. Add one row of verified evidence at a time. Put user-requested comment responses behind the publishing workflow in the docs and demonstrate them only after testing the intended platform flow.
4. **Choose a license and ship a release.** The current README links to MIT but the repository has no LICENSE file. Confirm the license and rights to distribute the code and assets before adding the license badge. There was no GitHub release at audit time. When the supported flow is repeatable, publish a versioned preview with release notes and a named downloadable starter asset. List exactly what can be reproduced. [GitHub licensing](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) · [About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
5. **Launch with one real workflow.** Post a 20–35 second recording on LinkedIn or X. Open on the clip and its target channel. Show the local check, the verified publish, and the resulting post URL or per-platform status. End with one action: “Try the sample clip on GitHub.” Share a technical write-up in a relevant community where project posts are welcome. Recruit a small group of creators who already export vertical clips, and ask them to report where the flow breaks.
6. **Review the first 14 days.** Use GitHub Insights → Traffic for unique visitors, referrers and full clones. Track stars as interest, named release-asset downloads as distribution, and successful checks reported by testers as adoption evidence. If visits are low, improve distribution and the opening hook. If visitors arrive but few try it, move the sample and result closer to the top. If people clone but fail setup, fix the first repeated error before another promotion push. [GitHub Traffic](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository)

## Suggested proof for the first announcement

- **Opening line** — I’m building a self-hosted way to publish short videos from a Python workflow.
- **First shot** — The sample video and the local check result.
- **Second shot** — One authorized account and a real successful publication.
- **Last frame** — UAAF Social Publisher · Try the sample clip on GitHub.

If the publishing test is still pending, share the local check as a small preview and ask for setup feedback.

## Handoff

The ZIP contains a replacement GitHub README, its media, a sample clip, and the matching social card and launch guide. Merge the README, `media/` and `examples/` into the repository root. The launch guide and social card can stay outside the repository. The current .gitignore excludes JPG, PNG and MP4 files. From the repository root, stage these exact files so the hero and sample are included.

```sh
git add README.md examples/check_clip.py media/video-check.gif
git add -f media/uaaf-hero.jpg media/uaaf-mark.png media/video-check.png examples/sample-vertical.mp4
```

The hero art is generated from the brief “An original editorial paper sculpture of one vertical sunset film frame fanning out into smaller video cards on deep aubergine.” The layout and typography were composed for UAAF. Local validator output was reproduced from repository commit `1ec12ac` with Python 3.12 and FFmpeg on Windows. This check covered a three-second vertical sample and a rotated landscape derivative. Live publishing and full scheduler setup are pending.


