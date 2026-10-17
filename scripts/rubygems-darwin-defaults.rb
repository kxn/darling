# Preserve Apple's Ruby 2.6 gem directories after upgrading RubyGems.
module Gem
  def self.default_dir
    '/Library/Ruby/Gems/2.6.0'
  end
  def self.default_path
    [user_dir, default_dir, '/System/Library/Frameworks/Ruby.framework/Versions/2.6/usr/lib/ruby/gems/2.6.0']
  end
  def self.default_specifications_dir
    '/System/Library/Frameworks/Ruby.framework/Versions/2.6/usr/lib/ruby/gems/2.6.0/specifications/default'
  end
end
