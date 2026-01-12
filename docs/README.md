# Lost Meadows Research Project Website

This directory contains the GitHub Pages website for the Lost Meadows science research project.

## Deployment Instructions

### Option 1: Deploy from Website folder (Recommended)

1. Go to your GitHub repository settings
2. Navigate to "Pages" section in the left sidebar
3. Under "Source", select "Deploy from a branch"
4. Choose "main" branch and "/Website" folder
5. Click "Save"

Your site will be available at: `https://[your-username].github.io/Lost-Meadows`

### Option 2: Deploy from root directory

If you prefer to deploy from the root directory:

1. Move all files from `Website/` to the root directory
2. Go to repository settings > Pages
3. Choose "main" branch and "/ (root)" folder
4. Click "Save"

## Customizing Your Website

### Adding Your Project Information

Edit `index.html` and replace the placeholder content:

- **Project Description**: Replace `[insert project description here]` with your actual project description
- **Research Objectives**: Update the objectives list with your specific goals
- **Methodology**: Add your research methods and approach
- **Timeline**: Insert your project timeline and current phase
- **Findings**: Replace placeholder findings with your actual research results
- **Publications**: Add links to your publications and resources
- **Contact Information**: Update the contact section with your details

### Adding Your Video

To add your ultrathink video, replace the video placeholder section in `index.html`:

#### For YouTube videos:
```html
<div class="video-container">
    <iframe width="100%" height="400" src="https://www.youtube.com/embed/VIDEO_ID"
            frameborder="0" allowfullscreen></iframe>
</div>
```

#### For Vimeo videos:
```html
<div class="video-container">
    <iframe width="100%" height="400" src="https://player.vimeo.com/video/VIDEO_ID"
            frameborder="0" allowfullscreen></iframe>
</div>
```

#### For direct MP4 uploads:
```html
<div class="video-container">
    <video width="100%" height="400" controls>
        <source src="path/to/your/video.mp4" type="video/mp4">
        Your browser does not support the video tag.
    </video>
</div>
```

### Customizing Styles

Modify `styles.css` to change:
- Colors (update the CSS custom properties)
- Fonts (change the font-family declarations)
- Layout (modify grid and flexbox properties)
- Responsive breakpoints

### Configuration

Update `_config.yml` to customize:
- Site title and description
- URL (replace with your actual GitHub Pages URL)
- Author information
- SEO settings

## File Structure

```
Website/
├── index.html          # Main website content
├── styles.css          # Stylesheet
├── _config.yml         # Jekyll configuration
└── README.md           # This file
```

## Local Development

To test your website locally before deploying:

1. Install Jekyll: `gem install bundler jekyll`
2. Navigate to the Website directory: `cd Website`
3. Run: `bundle exec jekyll serve`
4. Open `http://localhost:4000` in your browser

## Support

For GitHub Pages documentation, visit: https://docs.github.com/en/pages

For Jekyll documentation, visit: https://jekyllrb.com/docs/