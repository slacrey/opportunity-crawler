fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("failed to run opportunity crawler desktop shell");
}

#[cfg(test)]
mod tests {
    use std::{fs::File, io::BufReader, path::PathBuf};

    #[test]
    fn app_icon_decodes_to_tauri_rgba_input() {
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let icon = File::open(manifest_dir.join("icons/icon.png")).expect("icon.png exists");
        let decoder = png::Decoder::new(BufReader::new(icon));
        let mut reader = decoder.read_info().expect("icon.png metadata is readable");

        assert_eq!(reader.output_color_type().0, png::ColorType::Rgba);
        assert_eq!((reader.info().width, reader.info().height), (512, 512));

        let mut rgba: Vec<u8> = Vec::with_capacity(reader.output_buffer_size());
        while let Some(row) = reader.next_row().expect("icon.png row decodes") {
            rgba.extend(row.data());
        }

        assert_eq!(rgba.len(), 512 * 512 * 4);
    }
}
