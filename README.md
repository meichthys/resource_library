# Resource Library

A [Frappe](https://frappeframework.com/) app for collecting, curating and publishing freely given resources, built for [freely.giving](https://freely.giving).

[![License](https://img.shields.io/github/license/meichthys/resource_library)](license.txt)
[![Stars](https://img.shields.io/github/stars/meichthys/resource_library)](https://github.com/meichthys/resource_library/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/meichthys/resource_library)](https://github.com/meichthys/resource_library/commits)
[![Open Issues](https://img.shields.io/github/issues/meichthys/resource_library)](https://github.com/meichthys/resource_library/issues)
[![Release](https://img.shields.io/github/v/release/meichthys/resource_library)](https://github.com/meichthys/resource_library/releases)

## Screenshots

| Library Grid View | Resource Detail View |
| :---: | :---: |
| [![The /resources grid](docs/screenshots/browse.png)](docs/screenshots/browse.png) | [![One resource's page](docs/screenshots/resource.png)](docs/screenshots/resource.png) |

| Submit a Resource | Admin Dashboard |
| :---: | :---: |
| [![The submission form](docs/screenshots/submit.png)](docs/screenshots/submit.png) | [![The Resource Library workspace](docs/screenshots/workspace.png)](docs/screenshots/workspace.png) |

## What it does

**Public site**

- A searchable, filterable library of resources, grouped by a category tree and cross cut by tags.
- Favourites and a curated "Recommended" flag, both usable as filters.
- Similar resources on every listing, ranked by shared tags first and category proximity second.
- Embeddable "Recommended on Freely.Giving" badges, generated on demand so they stop working the moment a resource is unpublished.

**Submissions**

- Anyone signed in can submit a resource, and see their own submissions with their approval status.
- Submitters can request tags and categories that do not exist yet. A requested category can be filed under an existing one and marked as able to hold subcategories.
- Requests stay pending until an admin approves them. Nothing pending appears on the public site, and a resource cannot be published while its category is unapproved.

**Administration**

- A workspace with review queues: total and pending counts for resources, categories and tags.
- Ownership transfer, so a resource an admin filed on someone's behalf can be handed to the person it belongs to.
- Software resources carry repository and app store fields, required and shown only for categories in the Software branch.

## Installation

Install with the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/meichthys/resource_library --branch develop
bench --site $YOUR_SITE install-app resource_library
```

## Links

- [freely.giving](https://freely.giving), the site this app was built for
- [About](https://freely.giving/about) and [Why](https://freely.giving/why)
- [Publish](https://freely.giving/publish)

## License

[MIT-0](license.txt). No attribution required.

---

<a href="https://freely.giving">
  <img src="docs/freely.giving.png" alt="Freely given, no conditions. freely.giving" width="360">
</a>
